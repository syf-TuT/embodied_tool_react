# Realtime Simulation Observer Design

## Goal

Build a browser-based realtime observer for AI2-THOR episodes. The observer should show the current simulation frame, tool-call timeline, task status, failure information, and replanning events while preserving the existing offline experiment workflow.

## Chosen Approach

Use a lightweight FastAPI WebSocket server. `EpisodeRunner` emits structured observer events after reset, every tool call, replanning decisions, subtask checks, and episode completion. A web page connects to the server, receives JSON events, and renders the latest JPEG frame plus execution metadata.

This is preferred over file polling or one-way server-sent events because it gives good realtime behavior now and leaves a clean path to future manual controls such as pause, resume, or direct AI2-THOR actions.

## Requirements

- Keep existing batch and minimal scripts working without observer dependencies.
- Add observer support as an optional dependency path.
- Publish the latest AI2-THOR frame after each environment action.
- Publish structured state for:
  - task id, instruction, scene
  - step id and subtask id
  - tool name and arguments
  - success, message, and failure type
  - replan count and repair calls when available
  - agent pose and visible object summary
  - episode completion status
- Serve a browser UI at `http://localhost:8000`.
- Support Docker Desktop usage with `xvfb-run` and a published `8000` port.

## Architecture

### Observer Interface

Add `embodied_agent/observers/base.py` with a small `EpisodeObserver` protocol or base class. The runner calls methods such as:

- `on_episode_start(event)`
- `on_step(event)`
- `on_replan(event)`
- `on_subtask_result(event)`
- `on_episode_end(event)`

The default observer is `None`, so existing code paths are unchanged.

### Event Construction

`EpisodeRunner` remains responsible for high-level event timing because it knows the task, subtask, tool call, result, failure analysis, and replanning decisions.

`AI2ThorEnv` remains responsible for environment data. It already exposes `get_frame()`, `get_metadata()`, `get_visible_objects()`, and `get_agent_state()`. A helper will convert the frame into a compact browser-safe payload.

### Frame Encoding

Add `embodied_agent/observers/frame_encoding.py`.

The helper accepts the numpy RGB frame from AI2-THOR and returns a JPEG data URL or base64 JPEG string. Prefer Pillow for JPEG encoding because it is lightweight and common. The observer server can degrade gracefully when no frame is available.

### WebSocket Server

Add `embodied_agent/observers/web.py` and `scripts/run_observer_server.py`.

The server owns an event queue and broadcasts observer events to connected browser clients. It also serves the static UI. The first version can run a single episode per server process, which matches the current minimal experiment workflow.

### Browser UI

Create a simple static UI under `web/observer/`.

The UI should prioritize debugging usefulness:

- Large live simulation frame.
- Compact current task/status panel.
- Step timeline with success/failure styling.
- Current visible objects and agent state.
- Replan/failure messages in a scannable log.

No manual controls are required in this design. The layout should leave room for adding controls later.

## Data Flow

1. User starts `scripts/run_observer_server.py`.
2. FastAPI serves the observer page and accepts WebSocket clients.
3. The server starts one AI2-THOR episode using the existing planner, env, registry, and runner.
4. `EpisodeRunner` emits observer events during execution.
5. The web observer encodes the latest frame and broadcasts each event.
6. Browser updates the frame, timeline, and metadata panels.
7. Existing logger still writes the final trajectory, summary, metrics, and skill memory.

## Error Handling

- If no browser is connected, the episode should continue running.
- If frame encoding fails, send metadata without a frame and include an observer warning.
- If AI2-THOR reset or action fails, preserve the current `ToolResult` behavior and publish the failure event.
- If the WebSocket disconnects, remove that client without stopping the episode.
- If the server cannot import FastAPI or Pillow, show a clear install message.

## Testing Strategy

- Unit test frame encoding with `None` and a small numpy frame.
- Unit test observer event emission using a fake observer and fake env.
- Keep existing runner tests passing with no observer configured.
- Add a script-level smoke test for importing the observer server without starting AI2-THOR.

## Run Command

Expected Docker command:

```powershell
docker compose run --rm -p 8000:8000 ai2thor xvfb-run -a python scripts/run_observer_server.py --platform linux64 --host 0.0.0.0 --port 8000
```

Expected local browser URL:

```text
http://localhost:8000
```
