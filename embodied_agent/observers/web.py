from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI


class WebObserver:
    def __init__(self, send_timeout: float = 1.0) -> None:
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.clients: set[Any] = set()
        self.send_timeout = send_timeout
        self._sequence = 0
        self._sequence_lock = threading.Lock()

    def on_event(self, event: dict[str, Any]) -> None:
        with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence
        enriched = dict(event)
        enriched["sequence"] = sequence
        self.queue.put_nowait(enriched)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def broadcast_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            event = await self._get_next_event(loop)
            stale_clients = await asyncio.gather(
                *(self._send_to_client(client, event) for client in list(self.clients))
            )
            for client in stale_clients:
                if client is not None:
                    self.disconnect(client)

    async def _get_next_event(
        self, loop: asyncio.AbstractEventLoop
    ) -> dict[str, Any]:
        while True:
            try:
                return await loop.run_in_executor(None, self.queue.get, True, 0.1)
            except queue.Empty:
                await asyncio.sleep(0)

    async def _send_to_client(self, client: Any, event: dict[str, Any]) -> Any | None:
        try:
            await asyncio.wait_for(client.send_json(event), timeout=self.send_timeout)
        except Exception:
            return client
        return None


def create_observer_app(observer: WebObserver, static_dir: Path) -> FastAPI:
    from fastapi import FastAPI, WebSocket
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI()

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    async def start_broadcast_loop() -> None:
        app.state.broadcast_task = asyncio.create_task(observer.broadcast_loop())

    @app.get("/")
    async def index():
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return HTMLResponse(
            "<html><body><h1>Realtime observer server is running.</h1>"
            "<p>Observer UI files are not installed yet.</p></body></html>"
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await observer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        finally:
            observer.disconnect(websocket)

    return app
