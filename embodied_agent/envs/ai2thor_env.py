from __future__ import annotations

from typing import Any, Optional

from embodied_agent.schemas.data_models import ToolResult


class AI2ThorEnv:
    """Thin wrapper around ai2thor.controller.Controller."""

    def __init__(
        self,
        scene: str = "FloorPlan1",
        grid_size: float = 0.25,
        visibility_distance: float = 1.5,
        controller_kwargs: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            from ai2thor.controller import Controller
        except ImportError as exc:
            raise RuntimeError(
                "ai2thor is not installed. Install it with `pip install ai2thor` "
                "before constructing AI2ThorEnv."
            ) from exc

        kwargs = controller_kwargs or {}
        try:
            self.controller = Controller(
                scene=scene,
                gridSize=grid_size,
                visibilityDistance=visibility_distance,
                **kwargs,
            )
        except ValueError as exc:
            if "arch=Windows" in str(exc):
                raise RuntimeError(
                    "AI2-THOR did not find a native Windows Unity build for this version. "
                    "Run the real Unity smoke test from Linux/macOS, or use WSL/Linux with "
                    "a supported AI2-THOR platform such as CloudRendering."
                ) from exc
            raise
        self.scene = scene
        self.last_event = getattr(self.controller, "last_event", None)

    def reset(self, scene: Optional[str] = None) -> ToolResult:
        if scene:
            self.scene = scene
        try:
            self.last_event = self.controller.reset(scene=self.scene)
            return ToolResult(True, "reset_success", observation={"metadata": self.get_metadata()})
        except Exception as exc:
            return ToolResult(False, str(exc), data={"failure_type": "reset_failed"})

    def step(self, action: str, **kwargs: Any) -> ToolResult:
        try:
            self.last_event = self.controller.step(action=action, **kwargs)
            metadata = self.get_metadata()
            success = bool(metadata.get("lastActionSuccess", False))
            message = metadata.get("errorMessage") or ("success" if success else "action_failed")
            return ToolResult(
                success=success,
                message=message,
                data={
                    "action": action,
                    "lastActionSuccess": success,
                    "errorMessage": metadata.get("errorMessage", ""),
                    "actionReturn": metadata.get("actionReturn"),
                },
                observation={"metadata": metadata},
            )
        except Exception as exc:
            return ToolResult(False, str(exc), data={"action": action, "failure_type": "action_exception"})

    def get_metadata(self) -> dict[str, Any]:
        if not self.last_event:
            return {}
        return getattr(self.last_event, "metadata", {}) or {}

    def get_objects(self) -> list[dict[str, Any]]:
        return list(self.get_metadata().get("objects", []))

    def get_visible_objects(self) -> list[dict[str, Any]]:
        return [obj for obj in self.get_objects() if obj.get("visible")]

    def get_inventory_objects(self) -> list[dict[str, Any]]:
        return list(self.get_metadata().get("inventoryObjects", []))

    def get_agent_state(self) -> dict[str, Any]:
        return dict(self.get_metadata().get("agent", {}))

    def get_frame(self) -> Any:
        return getattr(self.last_event, "frame", None)

    def stop(self) -> None:
        self.controller.stop()

    def get_reachable_positions(self) -> list[dict[str, Any]]:
        result = self.step("GetReachablePositions")
        if not result.success:
            return []
        action_return = result.data.get("actionReturn")
        return list(action_return or [])

    def teleport(self, position: dict[str, Any], rotation: float = 0.0, horizon: float = 0.0) -> ToolResult:
        return self.step(
            "TeleportFull",
            x=position["x"],
            y=position["y"],
            z=position["z"],
            rotation={"x": 0.0, "y": rotation, "z": 0.0},
            horizon=horizon,
            standing=True,
        )
