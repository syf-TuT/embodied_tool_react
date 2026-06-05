from __future__ import annotations

from embodied_agent.schemas.data_models import ToolResult


def make_simple_action(env, action: str):
    def tool() -> ToolResult:
        return env.step(action)

    return tool


def _visible_object(env, object_type: str) -> dict | None:
    for obj in env.get_visible_objects():
        if str(obj.get("objectType", "")).lower() == object_type.lower():
            return obj
    return None


def make_search_object(env):
    def search_object(object_type: str, max_rotations: int = 4) -> ToolResult:
        if _visible_object(env, object_type):
            return ToolResult(True, "object_visible", {"object_type": object_type})

        observations = []
        for _ in range(max_rotations):
            step_result = env.step("RotateRight")
            observations.append(step_result.to_dict())
            if _visible_object(env, object_type):
                return ToolResult(True, "object_found_after_rotation", {"object_type": object_type}, {"search_steps": observations})
            if not step_result.success:
                return step_result

        return ToolResult(False, "object_not_visible", {"failure_type": "object_not_visible", "object_type": object_type}, {"search_steps": observations})

    return search_object


def make_navigate_to_object(env):
    search_object = make_search_object(env)

    def navigate_to_object(object_type: str) -> ToolResult:
        if _visible_object(env, object_type):
            return ToolResult(True, "object_visible", {"object_type": object_type})
        return search_object(object_type)

    return navigate_to_object


def register_navigation_tools(registry, env) -> None:
    registry.register("move_ahead", make_simple_action(env, "MoveAhead"), "Move ahead", {})
    registry.register("rotate_left", make_simple_action(env, "RotateLeft"), "Rotate left", {})
    registry.register("rotate_right", make_simple_action(env, "RotateRight"), "Rotate right", {})
    registry.register("look_up", make_simple_action(env, "LookUp"), "Look up", {})
    registry.register("look_down", make_simple_action(env, "LookDown"), "Look down", {})
    registry.register("search_object", make_search_object(env), "Rotate to search for an object", {"object_type": str, "max_rotations": int})
    registry.register("navigate_to_object", make_navigate_to_object(env), "Minimal object navigation", {"object_type": str})
