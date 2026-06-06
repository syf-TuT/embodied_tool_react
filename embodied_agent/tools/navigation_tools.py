from __future__ import annotations

import math

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


def _objects_of_type(env, object_type: str) -> list[dict]:
    return [
        obj
        for obj in env.get_objects()
        if str(obj.get("objectType", "")).lower() == object_type.lower()
    ]


def _position_distance(a: dict, b: dict) -> float:
    ax = float(a.get("x", 0.0))
    az = float(a.get("z", 0.0))
    bx = float(b.get("x", 0.0))
    bz = float(b.get("z", 0.0))
    return math.hypot(ax - bx, az - bz)


def _object_distance(obj: dict) -> float:
    value = obj.get("distance")
    if value is None:
        return float("inf")
    return float(value)


def _yaw_to_object(position: dict, obj: dict) -> float:
    target = obj.get("position") or {}
    dx = float(target.get("x", 0.0)) - float(position.get("x", 0.0))
    dz = float(target.get("z", 0.0)) - float(position.get("z", 0.0))
    return math.degrees(math.atan2(dx, dz))


def _reachable_positions(env) -> list[dict]:
    if hasattr(env, "get_reachable_positions"):
        return list(env.get_reachable_positions())
    result = env.step("GetReachablePositions")
    if not result.success:
        return []
    return list(result.data.get("actionReturn") or [])


def _teleport(env, position: dict, rotation: float = 0.0, horizon: float = 0.0) -> ToolResult:
    if hasattr(env, "teleport"):
        return env.teleport(position, rotation=rotation, horizon=horizon)
    return env.step(
        "TeleportFull",
        x=position["x"],
        y=position["y"],
        z=position["z"],
        rotation={"x": 0.0, "y": rotation, "z": 0.0},
        horizon=horizon,
        standing=True,
    )


def _ranked_reachable_positions(env, object_type: str) -> list[dict]:
    positions = _reachable_positions(env)
    targets = [obj.get("position") for obj in _objects_of_type(env, object_type) if obj.get("position")]
    if not targets:
        return positions
    return sorted(positions, key=lambda pos: min(_position_distance(pos, target) for target in targets))


def _rotate_scan(env, object_type: str, max_rotations: int) -> tuple[dict | None, list[dict]]:
    observations = []
    visible = _visible_object(env, object_type)
    if visible:
        return visible, observations
    for _ in range(max_rotations):
        step_result = env.step("RotateRight")
        observations.append(step_result.to_dict())
        visible = _visible_object(env, object_type)
        if visible:
            return visible, observations
        if not step_result.success:
            break
    return None, observations


def make_search_object(env):
    def search_object(object_type: str, max_rotations: int = 4, max_positions: int = 12) -> ToolResult:
        observations = []
        visible, scan_steps = _rotate_scan(env, object_type, max_rotations)
        observations.extend(scan_steps)
        if visible:
            return ToolResult(True, "object_visible", {"object_type": object_type, "object": visible}, {"search_steps": observations})

        for position in _ranked_reachable_positions(env, object_type)[:max_positions]:
            target = _objects_of_type(env, object_type)
            rotation = _yaw_to_object(position, target[0]) if target else 0.0
            teleport_result = _teleport(env, position, rotation=rotation, horizon=15.0)
            observations.append(teleport_result.to_dict())
            if not teleport_result.success:
                continue
            visible, scan_steps = _rotate_scan(env, object_type, max_rotations)
            observations.extend(scan_steps)
            if visible:
                return ToolResult(
                    True,
                    "object_found_after_teleport",
                    {"object_type": object_type, "object": visible},
                    {"search_steps": observations},
                )

        return ToolResult(False, "object_not_visible", {"failure_type": "object_not_visible", "object_type": object_type}, {"search_steps": observations})

    return search_object


def make_navigate_to_object(env):
    search_object = make_search_object(env)

    def navigate_to_object(object_type: str, interaction_distance: float = 1.5) -> ToolResult:
        visible = _visible_object(env, object_type)
        if not visible:
            search_result = search_object(object_type)
            if not search_result.success:
                return search_result
            visible = _visible_object(env, object_type)
        if visible and _object_distance(visible) <= interaction_distance:
            return ToolResult(True, "object_interactable", {"object_type": object_type, "object": visible})

        for position in _ranked_reachable_positions(env, object_type):
            target = visible or (_objects_of_type(env, object_type) or [{}])[0]
            teleport_result = _teleport(env, position, rotation=_yaw_to_object(position, target), horizon=15.0)
            if not teleport_result.success:
                continue
            visible = _visible_object(env, object_type)
            if visible and _object_distance(visible) <= interaction_distance:
                return ToolResult(True, "object_interactable", {"object_type": object_type, "object": visible})

        return ToolResult(
            False,
            "object_not_reachable",
            {"failure_type": "object_not_reachable", "object_type": object_type},
        )

    return navigate_to_object


def register_navigation_tools(registry, env) -> None:
    registry.register("move_ahead", make_simple_action(env, "MoveAhead"), "Move ahead", {})
    registry.register("rotate_left", make_simple_action(env, "RotateLeft"), "Rotate left", {})
    registry.register("rotate_right", make_simple_action(env, "RotateRight"), "Rotate right", {})
    registry.register("look_up", make_simple_action(env, "LookUp"), "Look up", {})
    registry.register("look_down", make_simple_action(env, "LookDown"), "Look down", {})
    registry.register(
        "search_object",
        make_search_object(env),
        "Search for an object with rotation and reachable-position teleports",
        {"object_type": str, "max_rotations": int, "max_positions": int},
    )
    registry.register(
        "navigate_to_object",
        make_navigate_to_object(env),
        "Teleport near a visible or searchable object",
        {"object_type": str, "interaction_distance": float},
    )
