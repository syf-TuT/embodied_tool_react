# embodied_tool_react

Minimal Python framework for paper experiments on high-level embodied task planning in AI2-THOR, inspired by Code-as-Policy / CaP-X and ReAct-style tool use.

The first version focuses on the closed loop rather than low-level policy learning: planner -> tool calls -> AI2-THOR wrapper -> success detection -> failure analysis -> replanning -> memory -> metrics.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

AI2-THOR is optional for unit tests but required for real environment runs:

```powershell
.\.venv\Scripts\python.exe -m pip install ai2thor
```

## Run One Batch

```powershell
.\.venv\Scripts\python.exe main.py --config configs/default.yaml --tasks configs/tasks_ai2thor.json
```

Equivalent script entry:

```powershell
.\.venv\Scripts\python.exe scripts/run_experiments.py --config configs/default.yaml --tasks configs/tasks_ai2thor.json
```

## Run Real AI2-THOR Minimal Loop

After installing `ai2thor`, run one Unity scene task:

```powershell
.\.venv\Scripts\python.exe scripts/run_ai2thor_minimal.py --scene FloorPlan1 --instruction "put the apple in the fridge"
```

On Linux headless machines, use CloudRendering when Vulkan/NVIDIA support is
available:

```powershell
.\.venv\Scripts\python.exe scripts/run_ai2thor_minimal.py --platform cloudrendering
```

## Run In Docker Desktop

Docker Desktop can provide the Linux environment needed by the real AI2-THOR
Unity runtime. From the project root, build the image and run the minimal loop:

```powershell
docker compose up --build ai2thor
```

To override the scene or instruction:

```powershell
docker compose run --rm ai2thor xvfb-run -a python scripts/run_ai2thor_minimal.py --platform linux64 --scene FloorPlan1 --instruction "put the apple in the fridge" --max-steps 8 --server-timeout 20
```

To enter the Linux container for debugging:

```powershell
docker compose --profile shell run --rm ai2thor-shell
```

AI2-THOR downloads the Unity build on first launch, so the first run can take a
while. The Docker setup keeps that cache in the `ai2thor_cache` volume and
writes experiment outputs to `outputs/`. The compose entry uses `xvfb-run` with
AI2-THOR's Linux64 build, which works in Docker Desktop without requiring
CloudRendering/Vulkan GPU passthrough.

This uses the rule-based planner sequence:

```text
search_object("Apple")
pick_object("Apple")
search_object("Fridge")
open_object("Fridge")
put_object("Fridge")
```

The first real-navigation version uses reachable-position `TeleportFull` calls
instead of full path planning. This keeps the experiment focused on high-level
planning and tool repair rather than low-level locomotion.

Outputs are written to:

```text
outputs/
  trajectories/
  summary.csv
  metrics.json
  skill_memory.json
```

## Project Structure

```text
embodied_agent/
  envs/          AI2-THOR wrapper
  planners/      RuleBasedPlanner and MockLLMPlanner
  tools/         perception, navigation, interaction, state tools
  detectors/     success condition parser
  replanning/    failure analyzer and bounded replanner
  memory/        JSON skill memory
  runner/        episode closed-loop controller
  evaluation/    metrics and output logger
  schemas/       dataclass data models
```

## Supported Tools

- Perception: `detect_object`, `detect_visible_object`, `list_visible_objects`
- Navigation: `move_ahead`, `rotate_left`, `rotate_right`, `look_up`, `look_down`, `search_object`, `navigate_to_object`
- Interaction: `pick_object`, `put_object`, `open_object`, `close_object`
- State checks: `check_object_visible`, `check_object_in_inventory`, `check_object_on_receptacle`, `check_object_open`

## Supported Task Templates

- `pick up the mug`
- `put the mug on the countertop`
- `open the fridge`
- `put the apple in the fridge`

## Extension Points

To add a real LLM planner, subclass `BasePlanner` and make it return the same `Plan` / `SubTask` / `ToolCall` dataclasses. The `MockLLMPlanner` shows the JSON shape expected from future OpenAI, Gemini, or Qwen adapters.

To improve navigation, replace the minimal `navigate_to_object` with a policy based on AI2-THOR actions such as `GetReachablePositions`, `Teleport`, or a search/planning module. Keep the planner isolated from `controller.step`; only tools should call environment actions.
