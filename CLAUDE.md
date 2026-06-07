# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

embodied_tool_react is a Python framework for embodied task planning experiments in AI2-THOR. It implements closed-loop planning: planner → tool calls → environment → success detection → replanning. Inspired by Code-as-Policy and ReAct-style tool use patterns.

## Commands

```bash
# Run tasks
python main.py --config configs/default.yaml --tasks configs/tasks_ai2thor.json

# Run real-time web observer
python scripts/run_observer_server.py

# Run all tests
pytest

# Run a single test
pytest tests/test_tool_registry.py
pytest tests/test_success_detector.py -k "test_specific_name"

# Run tests without AI2-THOR (unit tests only)
pytest tests/test_tool_registry.py tests/test_success_detector.py tests/test_web_observer.py

# Docker (headless Linux execution)
docker compose up ai2thor
docker compose up ai2thor-observer
```

## Architecture

The system implements a closed-loop control cycle:

```
Planner → Plan(SubTasks) → EpisodeRunner → Tool Execution → AI2-THOR Environment
                ↑                                    ↓
          Replanner ← FailureAnalyzer ← SuccessDetector
```

### Core Loop (`embodied_agent/runner/episode_runner.py`)

EpisodeRunner orchestrates each episode: executes subtask tool calls sequentially, checks success conditions after each subtask, and triggers replanning on failure (up to `max_replans`). Emits events to observers.

### Planners (`embodied_agent/planners/`)

- `BasePlanner` — abstract interface returning `Plan` with `SubTask` list
- `RuleBasedPlanner` — template-based (pick_up, put_on, open, put_in)
- `MockLLMPlanner` — extension point for real LLM adapters (OpenAI/Gemini/Qwen)

### Tools (`embodied_agent/tools/`)

Categorized tool registry with factory registration pattern:
- **Perception**: detect_object, list_visible_objects
- **Navigation**: move_ahead, rotate_left/right, look_up/down, navigate_to_object
- **Interaction**: pick_object, put_object, open_object, close_object
- **State**: check_object_visible, check_object_in_inventory, check_object_on_receptacle

### Schemas (`embodied_agent/schemas/`)

Dataclasses: `ToolCall`, `ToolResult`, `Plan`, `SubTask`, `EpisodeResult`. Frozen immutability where appropriate.

### Observers (`embodied_agent/observers/`)

WebObserver streams real-time events over WebSocket (FastAPI + Uvicorn). Frontend in `web/observer/`.

### Configuration

- `configs/default.yaml` — scene, grid_size, visibility_distance, planner_type, max_steps, max_replans
- `configs/tasks_ai2thor.json` — task definitions (task_id, scene, instruction)

## Extension Points

1. **Custom Planners**: Subclass `BasePlanner`, return `Plan`/`SubTask`/`ToolCall` dataclasses
2. **Tool Registry**: Add tools via `register_*_tools` factory functions
3. **Navigation Policy**: Replace minimal `navigate_to_object` with pathfinding (GetReachablePositions, Teleport)
4. **Observers**: Implement `EpisodeObserver` interface for custom event handling

## Tech Stack

- Python 3.11, ai2thor 5.0+, FastAPI, Uvicorn, PyYAML, Pillow, NumPy
