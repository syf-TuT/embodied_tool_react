from __future__ import annotations

from ai2thor import platform

from embodied_agent.envs import AI2ThorEnv
from embodied_agent.factory import build_default_tool_registry
from embodied_agent.schemas.data_models import ToolCall


def main() -> None:
    env = AI2ThorEnv(
        scene="FloorPlan1",
        controller_kwargs={"platform": platform.Linux64, "width": 300, "height": 300},
    )
    try:
        print("before reset", flush=True)
        reset = env.reset("FloorPlan1")
        print(f"after reset success={reset.success} message={reset.message}", flush=True)

        registry = build_default_tool_registry(env)
        calls = [
            ToolCall("search_object", {"object_type": "Apple", "max_rotations": 1, "max_positions": 2}),
            ToolCall("pick_object", {"object_type": "Apple"}),
            ToolCall("search_object", {"object_type": "Fridge", "max_rotations": 1, "max_positions": 2}),
            ToolCall("open_object", {"object_type": "Fridge"}),
            ToolCall("put_object", {"receptacle_type": "Fridge"}),
        ]
        for call in calls:
            print(f"before tool {call.tool_name} {call.args}", flush=True)
            result = registry.execute(call)
            print(f"after tool {call.tool_name} success={result.success} message={result.message}", flush=True)
    finally:
        env.stop()
        print("stopped", flush=True)


if __name__ == "__main__":
    main()
