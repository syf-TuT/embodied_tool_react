from __future__ import annotations

from typing import Any

from embodied_agent.schemas.data_models import ToolResult


def _object_summary(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "objectId": obj.get("objectId"),
        "objectType": obj.get("objectType"),
        "visible": obj.get("visible", False),
        "position": obj.get("position"),
        "distance": obj.get("distance"),
        "pickupable": obj.get("pickupable", False),
        "openable": obj.get("openable", False),
        "receptacle": obj.get("receptacle", False),
        "isOpen": obj.get("isOpen"),
    }


def _matches_type(obj: dict[str, Any], object_type: str) -> bool:
    return str(obj.get("objectType", "")).lower() == object_type.lower()


def make_detect_object(env):
    def detect_object(object_type: str) -> ToolResult:
        matches = [_object_summary(obj) for obj in env.get_objects() if _matches_type(obj, object_type)]
        return ToolResult(bool(matches), "objects_found" if matches else "object_not_found", {"objects": matches, "count": len(matches)})

    return detect_object


def make_detect_visible_object(env):
    def detect_visible_object(object_type: str) -> ToolResult:
        matches = [_object_summary(obj) for obj in env.get_visible_objects() if _matches_type(obj, object_type)]
        return ToolResult(bool(matches), "visible_objects_found" if matches else "object_not_visible", {"objects": matches, "count": len(matches)})

    return detect_visible_object


def make_list_visible_objects(env):
    def list_visible_objects() -> ToolResult:
        objects = [_object_summary(obj) for obj in env.get_visible_objects()]
        return ToolResult(True, "visible_objects", {"objects": objects})

    return list_visible_objects


def register_perception_tools(registry, env) -> None:
    registry.register("detect_object", make_detect_object(env), "Find objects by type", {"object_type": str})
    registry.register("detect_visible_object", make_detect_visible_object(env), "Find visible objects by type", {"object_type": str})
    registry.register("list_visible_objects", make_list_visible_objects(env), "List visible objects", {})
