from __future__ import annotations

from typing import Any, Protocol


class EpisodeObserver(Protocol):
    def on_event(self, event: dict[str, Any]) -> None:
        ...
