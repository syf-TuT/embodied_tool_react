from __future__ import annotations

import asyncio
import queue
import threading
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI


class WebObserver:
    def __init__(self, send_timeout: float = 1.0, history_limit: int = 100) -> None:
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.clients: set[Any] = set()
        self._client_sent_sequence: dict[Any, int] = {}
        self._client_send_locks: dict[Any, asyncio.Lock] = {}
        self.send_timeout = send_timeout
        self.history: deque[dict[str, Any]] = deque(maxlen=history_limit)
        self._history_lock = threading.Lock()
        self._sequence = 0
        self._sequence_lock = threading.Lock()

    def on_event(self, event: dict[str, Any]) -> None:
        with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence
        enriched = dict(event)
        enriched["sequence"] = sequence
        with self._history_lock:
            self.history.append(enriched)
        self.queue.put_nowait(enriched)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self._client_sent_sequence[websocket] = 0
        self._client_send_locks[websocket] = asyncio.Lock()
        while True:
            with self._history_lock:
                pending_events = [
                    event
                    for event in self.history
                    if int(event.get("sequence", 0))
                    > self._client_sent_sequence.get(websocket, 0)
                ]
                if not pending_events:
                    self.clients.add(websocket)
                    return

            for event in pending_events:
                stale_client = await self._send_to_client(websocket, event)
                if stale_client is not None:
                    self.disconnect(websocket)
                    return

    def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)
        self._client_sent_sequence.pop(websocket, None)
        self._client_send_locks.pop(websocket, None)

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
        lock = self._client_send_locks.setdefault(client, asyncio.Lock())
        async with lock:
            sequence = int(event.get("sequence", 0))
            if sequence <= self._client_sent_sequence.get(client, 0):
                return None
            try:
                await asyncio.wait_for(
                    client.send_json(event), timeout=self.send_timeout
                )
            except Exception:
                return client
            self._client_sent_sequence[client] = max(
                sequence,
                self._client_sent_sequence.get(client, 0),
            )
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

    @app.on_event("shutdown")
    async def stop_broadcast_loop() -> None:
        task = getattr(app.state, "broadcast_task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

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
