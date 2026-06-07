from __future__ import annotations

import asyncio
from typing import Any


class WebObserver:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.clients: set[Any] = set()
        self._sequence = 0

    def on_event(self, event: dict[str, Any]) -> None:
        self._sequence += 1
        enriched = dict(event)
        enriched["sequence"] = self._sequence
        self.queue.put_nowait(enriched)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def broadcast_loop(self) -> None:
        while True:
            event = await self.queue.get()
            stale_clients = []
            for client in list(self.clients):
                try:
                    await client.send_json(event)
                except Exception:
                    stale_clients.append(client)
            for client in stale_clients:
                self.disconnect(client)
