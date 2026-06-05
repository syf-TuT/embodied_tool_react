from __future__ import annotations

from embodied_agent.schemas.data_models import ToolResult


def _type_matches(obj: dict, object_type: str) -> bool:
    return str(obj.get("objectType", "")).lower() == object_type.lower()


def check_object_visible(env, object_type: str) -> ToolResult:
    matches = [obj for obj in env.get_visible_objects() if _type_matches(obj, object_type)]
    return ToolResult(bool(matches), "object_visible" if matches else "object_not_visible", {"objects": matches})


def check_object_in_inventory(env, object_type: str) -> ToolResult:
    matches = [obj for obj in env.get_inventory_objects() if _type_matches(obj, object_type)]
    return ToolResult(bool(matches), "object_in_inventory" if matches else "object_not_in_inventory", {"objects": matches})


def check_object_on_receptacle(env, object_type: str, receptacle_type: str) -> ToolResult:
    receptacle_ids = {obj.get("objectId") for obj in env.get_objects() if _type_matches(obj, receptacle_type)}
    for obj in env.get_objects():
        parents = set(obj.get("parentReceptacles") or [])
        if _type_matches(obj, object_type) and parents.intersection(receptacle_ids):
            return ToolResult(True, "object_on_receptacle", {"object": obj, "matched": True})
    return ToolResult(False, "object_not_on_receptacle", {"matched": False})


def check_object_open(env, object_type: str) -> ToolResult:
    matches = [obj for obj in env.get_objects() if _type_matches(obj, object_type) and obj.get("isOpen")]
    return ToolResult(bool(matches), "object_open" if matches else "object_not_open", {"objects": matches})


def register_state_tools(registry, env) -> None:
    registry.register("check_object_visible", lambda object_type: check_object_visible(env, object_type), "Check object visibility", {"object_type": str})
    registry.register("check_object_in_inventory", lambda object_type: check_object_in_inventory(env, object_type), "Check inventory", {"object_type": str})
    registry.register(
        "check_object_on_receptacle",
        lambda object_type, receptacle_type: check_object_on_receptacle(env, object_type, receptacle_type),
        "Check object placement",
        {"object_type": str, "receptacle_type": str},
    )
    registry.register("check_object_open", lambda object_type: check_object_open(env, object_type), "Check open state", {"object_type": str})
