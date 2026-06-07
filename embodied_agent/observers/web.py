from __future__ import annotations

import asyncio
import threading
from typing import Any


class WebObserver:
    def __init__(self, send_timeout: float = 1.0) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.clients: set[Any] = set()
        self.send_timeout = send_timeout
        self._sequence = 0
        self._sequence_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def on_event(self, event: dict[str, Any]) -> None:
        with self._sequence_lock:
            self._sequence += 1
            sequence = self._sequence
        enriched = dict(event)
        enriched["sequence"] = sequence
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self.queue.put_nowait, enriched)
        else:
            self.queue.put_nowait(enriched)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def broadcast_loop(self) -> None:
        self._loop = asyncio.get_running_loop()
        while True:
            event = await self.queue.get()
            stale_clients = await asyncio.gather(
                *(self._send_to_client(client, event) for client in list(self.clients))
            )
            for client in stale_clients:
                if client is not None:
                    self.disconnect(client)

    async def _send_to_client(self, client: Any, event: dict[str, Any]) -> Any | None:
        try:
            await asyncio.wait_for(client.send_json(event), timeout=self.send_timeout)
        except Exception:
            return client
        return None
