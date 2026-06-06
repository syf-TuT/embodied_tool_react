from __future__ import annotations

from embodied_agent.schemas.data_models import ToolResult
from embodied_agent.tools.navigation_tools import make_navigate_to_object


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


def _should_retry_after_navigation(result: ToolResult, obj: dict, interaction_distance: float = 1.5) -> bool:
    if result.data.get("failure_type") != "action_failed":
        return False
    message = result.message.lower()
    if any(token in message for token in ["too_far", "too far", "not close", "distance"]):
        return True
    distance = obj.get("distance")
    return distance is not None and float(distance) > interaction_distance


def make_pick_object(env):
    navigate_to_object = make_navigate_to_object(env)

    def pick_object(object_type: str) -> ToolResult:
        obj, failure = _find_visible(env, object_type, "pickupable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        result = env.step("PickupObject", objectId=obj.get("objectId"))
        if result.success or not _should_retry_after_navigation(result, obj):
            return result
        navigation = navigate_to_object(object_type)
        if not navigation.success:
            return result
        obj, failure = _find_visible(env, object_type, "pickupable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        return env.step("PickupObject", objectId=obj.get("objectId"))

    return pick_object


def make_put_object(env):
    navigate_to_object = make_navigate_to_object(env)

    def put_object(receptacle_type: str) -> ToolResult:
        obj, failure = _find_visible(env, receptacle_type, "receptacle")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "receptacle_type": receptacle_type})
        result = env.step("PutObject", objectId=obj.get("objectId"))
        if result.success or not _should_retry_after_navigation(result, obj):
            return result
        navigation = navigate_to_object(receptacle_type)
        if not navigation.success:
            return result
        obj, failure = _find_visible(env, receptacle_type, "receptacle")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "receptacle_type": receptacle_type})
        return env.step("PutObject", objectId=obj.get("objectId"))

    return put_object


def make_open_object(env):
    navigate_to_object = make_navigate_to_object(env)

    def open_object(object_type: str) -> ToolResult:
        obj, failure = _find_visible(env, object_type, "openable")
        if not obj:
            return ToolResult(False, failure, {"failure_type": failure, "object_type": object_type})
        result = env.step("OpenObject", objectId=obj.get("objectId"))
        if result.success or not _should_retry_after_navigation(result, obj):
            return result
        navigation = navigate_to_object(object_type)
        if not navigation.success:
            return result
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
