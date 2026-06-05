from __future__ import annotations

from embodied_agent.schemas.data_models import ToolResult


def _find_visible(env, object_type: str, required_flag: str | None = None) -> tuple[dict | None, str]:
    seen_type = False
    for obj in env.get_visible_objects():
        if str(obj.get("objectType", "")).lower() != object_type.lower():
            continue
        seen_type = True
        if required_flag and not obj.get(required_flag, False):
            continue
        return obj, ""
    if not seen_type:
        return None, "object_not_visible"
    if required_flag == "pickupable":
        return None, "object_not_pickupable"
    if required_flag == "openable":
        return None, "object_not_openable"
    if required_flag == "receptacle":
        return None, "wrong_receptacle"
    return None, "object_not_visible"


def make_pick_object(env):
    def pick_object(object_type: str) -> ToolResult:
        obj, failure = _find_visible(env, object_type, "pickupable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        return env.step("PickupObject", objectId=obj.get("objectId"))

    return pick_object


def make_put_object(env):
    def put_object(receptacle_type: str) -> ToolResult:
        obj, failure = _find_visible(env, receptacle_type, "receptacle")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "receptacle_type": receptacle_type})
        return env.step("PutObject", objectId=obj.get("objectId"))

    return put_object


def make_open_object(env):
    def open_object(object_type: str) -> ToolResult:
        obj, failure = _find_visible(env, object_type, "openable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        return env.step("OpenObject", objectId=obj.get("objectId"))

    return open_object


def make_close_object(env):
    def close_object(object_type: str) -> ToolResult:
        obj, failure = _find_visible(env, object_type, "openable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        return env.step("CloseObject", objectId=obj.get("objectId"))

    return close_object


def register_interaction_tools(registry, env) -> None:
    registry.register("pick_object", make_pick_object(env), "Pick up a visible pickupable object", {"object_type": str})
    registry.register("put_object", make_put_object(env), "Put held object on/in a receptacle", {"receptacle_type": str})
    registry.register("open_object", make_open_object(env), "Open a visible openable object", {"object_type": str})
    registry.register("close_object", make_close_object(env), "Close a visible openable object", {"object_type": str})
