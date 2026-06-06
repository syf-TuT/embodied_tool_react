from __future__ import annotations

from ai2thor import platform
from ai2thor.controller import Controller


def main() -> None:
    print("create controller", flush=True)
    controller = Controller(
        platform=platform.Linux64,
        scene="FloorPlan1",
        width=300,
        height=300,
    )
    print("controller ready", flush=True)

    print("before reset", flush=True)
    event = controller.reset(scene="FloorPlan1")
    print(f"after reset success={event.metadata.get('lastActionSuccess')}", flush=True)

    actions = [
        ("GetReachablePositions", {}),
        ("RotateRight", {}),
    ]
    positions = []
    for action, kwargs in actions:
        print(f"before {action}", flush=True)
        event = controller.step(action=action, **kwargs)
        success = event.metadata.get("lastActionSuccess")
        action_return = event.metadata.get("actionReturn")
        count = len(action_return) if isinstance(action_return, list) else "-"
        print(f"after {action} success={success} action_return_count={count}", flush=True)
        if action == "GetReachablePositions":
            positions = action_return or []

    if positions:
        position = positions[0]
        print("before TeleportFull", flush=True)
        event = controller.step(
            action="TeleportFull",
            x=position["x"],
            y=position["y"],
            z=position["z"],
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            horizon=0.0,
            standing=True,
        )
        print(f"after TeleportFull success={event.metadata.get('lastActionSuccess')}", flush=True)

    controller.stop()
    print("stopped", flush=True)


if __name__ == "__main__":
    main()
