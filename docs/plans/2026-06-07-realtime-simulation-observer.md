# Realtime Simulation Observer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a browser-based realtime observer that streams AI2-THOR frames and execution events during an episode.

**Architecture:** Add an optional observer interface to `EpisodeRunner`, emit structured events at reset, step, replan, subtask, and finish boundaries, and implement a FastAPI WebSocket observer server that broadcasts those events to a static browser UI. Existing offline scripts keep working because `observer=None` is the default.

**Tech Stack:** Python `unittest`, AI2-THOR frame arrays, Pillow for JPEG encoding, FastAPI/Uvicorn/WebSocket for realtime browser delivery, static HTML/CSS/JS for the UI.

---

### Task 1: Add Observer Interface And Runner Event Hooks

**Files:**
- Create: `embodied_agent/observers/__init__.py`
- Create: `embodied_agent/observers/base.py`
- Modify: `embodied_agent/runner/episode_runner.py`
- Test: `tests/test_episode_observer.py`

**Step 1: Write the failing tests**

Create `tests/test_episode_observer.py`:

```python
import unittest

from embodied_agent.factory import build_default_tool_registry
from embodied_agent.planners import RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner
from embodied_agent.schemas.data_models import ToolResult


class RecordingObserver:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


class ObserverEnv:
    def __init__(self):
        self.agent_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.inventory = []
        self.objects = [
            {
                "objectId": "Mug|1",
                "objectType": "Mug",
                "visible": True,
                "pickupable": True,
                "position": {"x": 0.5, "y": 0.9, "z": 0.0},
                "distance": 0.5,
            }
        ]

    def reset(self, scene):
        return ToolResult(True, "reset_success", observation={"metadata": self.get_metadata()})

    def get_metadata(self):
        return {
            "objects": self.objects,
            "inventoryObjects": self.inventory,
            "agent": {"position": self.agent_position},
            "lastActionSuccess": True,
        }

    def get_objects(self):
        return self.objects

    def get_visible_objects(self):
        return [obj for obj in self.objects if obj.get("visible")]

    def get_inventory_objects(self):
        return self.inventory

    def get_agent_state(self):
        return {"position": self.agent_position}

    def get_frame(self):
        return None

    def step(self, action, **kwargs):
        if action == "PickupObject":
            self.inventory = [{"objectId": "Mug|1", "objectType": "Mug"}]
            self.objects[0]["visible"] = False
            return ToolResult(True, "picked", observation={"metadata": self.get_metadata()})
        return ToolResult(True, "ok", observation={"metadata": self.get_metadata()})


class EpisodeObserverTest(unittest.TestCase):
    def test_runner_emits_episode_step_and_end_events(self):
        observer = RecordingObserver()
        env = ObserverEnv()
        runner = EpisodeRunner(
            env,
            RuleBasedPlanner(),
            build_default_tool_registry(env),
            max_steps=10,
            observer=observer,
        )

        result = runner.run("task_observe", "pick up the mug", "FloorPlan1")

        event_types = [event["type"] for event in observer.events]
        self.assertTrue(result.success)
        self.assertEqual(event_types[0], "episode_start")
        self.assertIn("step", event_types)
        self.assertEqual(event_types[-1], "episode_end")
        step_event = next(event for event in observer.events if event["type"] == "step")
        self.assertEqual(step_event["tool_name"], "pick_object")
        self.assertEqual(step_event["task_id"], "task_observe")
        self.assertIn("visible_objects", step_event)
        self.assertIn("agent", step_event)
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_episode_observer -v
```

Expected: FAIL because `EpisodeRunner.__init__` does not accept `observer`.

**Step 3: Implement the minimal observer interface**

Create `embodied_agent/observers/base.py`:

```python
from __future__ import annotations

from typing import Any, Protocol


class EpisodeObserver(Protocol):
    def on_event(self, event: dict[str, Any]) -> None:
        ...
```

Create `embodied_agent/observers/__init__.py`:

```python
from embodied_agent.observers.base import EpisodeObserver

__all__ = ["EpisodeObserver"]
```

Modify `EpisodeRunner.__init__` to accept `observer=None` and store it. Add helpers:

```python
def _emit(self, event: dict[str, Any]) -> None:
    if self.observer:
        self.observer.on_event(event)

def _observer_state(self) -> dict[str, Any]:
    visible = []
    if hasattr(self.env, "get_visible_objects"):
        for obj in self.env.get_visible_objects():
            visible.append({
                "objectId": obj.get("objectId"),
                "objectType": obj.get("objectType"),
                "distance": obj.get("distance"),
                "visible": obj.get("visible"),
            })
    agent = self.env.get_agent_state() if hasattr(self.env, "get_agent_state") else {}
    return {"agent": agent, "visible_objects": visible}
```

Emit `episode_start` after reset and plan creation, emit `step` after each trajectory step append, emit `replan` when repair calls are queued, emit `subtask_result` after each success detector check, and emit `episode_end` before returning the result.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_episode_observer -v
```

Expected: PASS.

**Step 5: Run existing runner tests**

Run:

```powershell
python -m unittest tests.test_ai2thor_minimal_loop -v
```

Expected: PASS, proving the default `observer=None` path did not regress.

**Step 6: Commit**

```powershell
git add embodied_agent/observers embodied_agent/runner/episode_runner.py tests/test_episode_observer.py
git commit -m "feat: add episode observer events"
```

### Task 2: Add Frame Encoding

**Files:**
- Create: `embodied_agent/observers/frame_encoding.py`
- Test: `tests/test_frame_encoding.py`
- Modify: `requirements.txt`

**Step 1: Write the failing tests**

Create `tests/test_frame_encoding.py`:

```python
import unittest

import numpy as np

from embodied_agent.observers.frame_encoding import encode_frame_jpeg_data_url


class FrameEncodingTest(unittest.TestCase):
    def test_none_frame_returns_none(self):
        self.assertIsNone(encode_frame_jpeg_data_url(None))

    def test_numpy_rgb_frame_encodes_to_jpeg_data_url(self):
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        frame[0, 0] = [255, 0, 0]

        encoded = encode_frame_jpeg_data_url(frame, quality=70)

        self.assertTrue(encoded.startswith("data:image/jpeg;base64,"))
        self.assertGreater(len(encoded), 40)
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_frame_encoding -v
```

Expected: FAIL because `frame_encoding.py` does not exist.

**Step 3: Add dependencies**

Modify `requirements.txt`:

```text
ai2thor>=5.0.0
PyYAML>=6.0.0
Pillow>=10.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
numpy>=1.24.0
```

**Step 4: Implement frame encoding**

Create `embodied_agent/observers/frame_encoding.py`:

```python
from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PIL import Image


def encode_frame_jpeg_data_url(frame: Any, quality: int = 75) -> str | None:
    if frame is None:
        return None
    image = Image.fromarray(frame)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
```

**Step 5: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_frame_encoding -v
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add requirements.txt embodied_agent/observers/frame_encoding.py tests/test_frame_encoding.py
git commit -m "feat: encode observer frames"
```

### Task 3: Add WebSocket Observer Broadcaster

**Files:**
- Create: `embodied_agent/observers/web.py`
- Test: `tests/test_web_observer.py`

**Step 1: Write the failing tests**

Create `tests/test_web_observer.py`:

```python
import asyncio
import unittest

from embodied_agent.observers.web import WebObserver


class WebObserverTest(unittest.TestCase):
    def test_on_event_enqueues_event_without_clients(self):
        observer = WebObserver()
        observer.on_event({"type": "step", "step_id": 1})

        event = observer.queue.get_nowait()

        self.assertEqual(event["type"], "step")
        self.assertEqual(event["step_id"], 1)

    def test_adds_sequence_number(self):
        observer = WebObserver()
        observer.on_event({"type": "episode_start"})
        observer.on_event({"type": "episode_end"})

        first = observer.queue.get_nowait()
        second = observer.queue.get_nowait()

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_web_observer -v
```

Expected: FAIL because `web.py` does not exist.

**Step 3: Implement broadcaster shell**

Create `embodied_agent/observers/web.py`:

```python
from __future__ import annotations

import asyncio
from typing import Any


class WebObserver:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.clients: set[Any] = set()
        self._sequence = 0

    def on_event(self, event: dict[str, Any]) -> None:
        self._sequence += 1
        enriched = dict(event)
        enriched["sequence"] = self._sequence
        self.queue.put_nowait(enriched)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def broadcast_loop(self) -> None:
        while True:
            event = await self.queue.get()
            stale = []
            for client in list(self.clients):
                try:
                    await client.send_json(event)
                except Exception:
                    stale.append(client)
            for client in stale:
                self.disconnect(client)
```

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_web_observer -v
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add embodied_agent/observers/web.py tests/test_web_observer.py
git commit -m "feat: add websocket observer broadcaster"
```

### Task 4: Add Observer Server Script

**Files:**
- Create: `scripts/run_observer_server.py`
- Modify: `embodied_agent/observers/web.py`
- Test: `tests/test_observer_server_import.py`

**Step 1: Write import smoke test**

Create `tests/test_observer_server_import.py`:

```python
import importlib.util
import unittest
from pathlib import Path


class ObserverServerImportTest(unittest.TestCase):
    def test_server_script_imports_without_starting_ai2thor(self):
        path = Path("scripts/run_observer_server.py")
        spec = importlib.util.spec_from_file_location("run_observer_server", path)
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "create_app"))
        self.assertTrue(hasattr(module, "main"))
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_observer_server_import -v
```

Expected: FAIL because the script does not exist.

**Step 3: Extend `web.py` with FastAPI app factory**

Add:

```python
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def create_observer_app(observer: WebObserver, static_dir: Path) -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    async def start_broadcast_loop() -> None:
        asyncio.create_task(observer.broadcast_loop())

    @app.get("/")
    async def index():
        return FileResponse(static_dir / "index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await observer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            observer.disconnect(websocket)

    return app
```

**Step 4: Create server script**

Create `scripts/run_observer_server.py` with:

```python
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from embodied_agent.envs import AI2ThorEnv
from embodied_agent.evaluation.logger import ExperimentLogger
from embodied_agent.factory import build_default_tool_registry
from embodied_agent.memory import SkillMemory
from embodied_agent.observers.frame_encoding import encode_frame_jpeg_data_url
from embodied_agent.observers.web import WebObserver, create_observer_app
from embodied_agent.planners import RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner


class FrameWebObserver(WebObserver):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def on_event(self, event):
        enriched = dict(event)
        try:
            enriched["frame"] = encode_frame_jpeg_data_url(self.env.get_frame())
        except Exception as exc:
            enriched["frame"] = None
            enriched["observer_warning"] = f"frame_encoding_failed: {exc}"
        super().on_event(enriched)


def run_episode(args, observer):
    controller_kwargs = {
        "width": args.width,
        "height": args.height,
        "server_timeout": args.server_timeout,
        "server_start_timeout": args.server_start_timeout,
    }
    if args.platform != "auto":
        from ai2thor import platform

        controller_kwargs["platform"] = {
            "cloudrendering": platform.CloudRendering,
            "linux64": platform.Linux64,
        }[args.platform]

    env = observer.env
    try:
        registry = build_default_tool_registry(env)
        runner = EpisodeRunner(
            env=env,
            planner=RuleBasedPlanner(),
            tool_registry=registry,
            max_steps=args.max_steps,
            max_replans=args.max_replans,
            memory=SkillMemory(Path(args.output_dir) / "skill_memory.json"),
            observer=observer,
        )
        result = runner.run(args.task_id, args.instruction, args.scene)
        logger = ExperimentLogger(args.output_dir)
        logger.save_episode(result)
        logger.save_summary([result])
        logger.save_metrics([result])
        print(json.dumps(result.to_dict(), indent=2))
    finally:
        env.stop()


def create_app(args=None):
    args = args or parse_args([])
    controller_kwargs = {
        "width": args.width,
        "height": args.height,
        "server_timeout": args.server_timeout,
        "server_start_timeout": args.server_start_timeout,
    }
    env = AI2ThorEnv(scene=args.scene, controller_kwargs=controller_kwargs)
    observer = FrameWebObserver(env)
    app = create_observer_app(observer, ROOT / "web" / "observer")
    app.state.observer = observer
    app.state.runner_thread = threading.Thread(target=run_episode, args=(args, observer), daemon=True)
    return app


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run AI2-THOR with a realtime browser observer.")
    parser.add_argument("--scene", default="FloorPlan1")
    parser.add_argument("--instruction", default="put the apple in the fridge")
    parser.add_argument("--task-id", default="ai2thor_observer_001")
    parser.add_argument("--output-dir", default="outputs/ai2thor_observer")
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--max-replans", type=int, default=3)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--server-timeout", type=float, default=20.0)
    parser.add_argument("--server-start-timeout", type=float, default=300.0)
    parser.add_argument("--platform", choices=["auto", "cloudrendering", "linux64"], default="auto")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def main():
    import uvicorn

    args = parse_args()
    app = create_app(args)

    @app.on_event("startup")
    async def start_episode():
        app.state.runner_thread.start()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

During implementation, avoid duplicating `controller_kwargs` by extracting a helper if the script starts to sprawl.

**Step 5: Run import smoke test**

Run:

```powershell
python -m unittest tests.test_observer_server_import -v
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add scripts/run_observer_server.py embodied_agent/observers/web.py tests/test_observer_server_import.py
git commit -m "feat: add observer server"
```

### Task 5: Add Browser Observer UI

**Files:**
- Create: `web/observer/index.html`
- Create: `web/observer/styles.css`
- Create: `web/observer/app.js`
- Test: `tests/test_observer_static_files.py`

**Step 1: Write static file test**

Create `tests/test_observer_static_files.py`:

```python
import unittest
from pathlib import Path


class ObserverStaticFilesTest(unittest.TestCase):
    def test_observer_ui_files_exist_and_reference_websocket(self):
        root = Path("web/observer")

        self.assertTrue((root / "index.html").exists())
        self.assertTrue((root / "styles.css").exists())
        self.assertTrue((root / "app.js").exists())
        self.assertIn("/ws", (root / "app.js").read_text(encoding="utf-8"))
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_observer_static_files -v
```

Expected: FAIL because the files do not exist.

**Step 3: Create `index.html`**

Build a real debugging interface, not a landing page:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI2-THOR Observer</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body>
    <main class="shell">
      <section class="viewport">
        <img id="frame" alt="AI2-THOR simulation frame">
        <div id="empty-frame">Waiting for frame</div>
      </section>
      <aside class="side">
        <header>
          <h1>AI2-THOR Observer</h1>
          <span id="connection">Connecting</span>
        </header>
        <section class="status">
          <div><span>Task</span><strong id="task">-</strong></div>
          <div><span>Scene</span><strong id="scene">-</strong></div>
          <div><span>Step</span><strong id="step">0</strong></div>
          <div><span>Status</span><strong id="status">Running</strong></div>
        </section>
        <section>
          <h2>Current Tool</h2>
          <pre id="current-tool">{}</pre>
        </section>
        <section>
          <h2>Visible Objects</h2>
          <ul id="objects"></ul>
        </section>
        <section>
          <h2>Timeline</h2>
          <ol id="timeline"></ol>
        </section>
      </aside>
    </main>
    <script src="/static/app.js"></script>
  </body>
</html>
```

**Step 4: Create `app.js`**

Implement connection, event rendering, and reconnect display. Use plain JavaScript:

```javascript
const frame = document.querySelector("#frame");
const emptyFrame = document.querySelector("#empty-frame");
const connection = document.querySelector("#connection");
const task = document.querySelector("#task");
const scene = document.querySelector("#scene");
const step = document.querySelector("#step");
const status = document.querySelector("#status");
const currentTool = document.querySelector("#current-tool");
const objects = document.querySelector("#objects");
const timeline = document.querySelector("#timeline");

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    connection.textContent = "Connected";
  });

  socket.addEventListener("message", (message) => {
    renderEvent(JSON.parse(message.data));
  });

  socket.addEventListener("close", () => {
    connection.textContent = "Disconnected";
    setTimeout(connect, 1200);
  });
}

function renderEvent(event) {
  if (event.task_id) task.textContent = event.task_id;
  if (event.scene) scene.textContent = event.scene;
  if (event.step_id) step.textContent = event.step_id;
  if (event.type === "episode_end") status.textContent = event.success ? "Success" : "Failed";
  if (event.frame) {
    frame.src = event.frame;
    frame.style.display = "block";
    emptyFrame.style.display = "none";
  }
  if (event.tool_name) {
    currentTool.textContent = JSON.stringify({
      tool: event.tool_name,
      args: event.args || {},
      success: event.success,
      message: event.message,
      failure_type: event.failure_type || "",
    }, null, 2);
  }
  renderObjects(event.visible_objects || []);
  appendTimeline(event);
}

function renderObjects(items) {
  objects.innerHTML = "";
  items.slice(0, 12).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.objectType || item.objectId} ${item.distance ?? ""}`;
    objects.appendChild(li);
  });
}

function appendTimeline(event) {
  const li = document.createElement("li");
  li.className = event.success === false ? "failed" : "ok";
  li.textContent = `${event.sequence}. ${event.type}${event.tool_name ? `: ${event.tool_name}` : ""}`;
  timeline.prepend(li);
}

connect();
```

**Step 5: Create `styles.css`**

Use a restrained debugging layout with stable dimensions. Avoid card nesting and large marketing hero styling.

**Step 6: Run static file test**

Run:

```powershell
python -m unittest tests.test_observer_static_files -v
```

Expected: PASS.

**Step 7: Commit**

```powershell
git add web/observer tests/test_observer_static_files.py
git commit -m "feat: add observer web ui"
```

### Task 6: Wire Docker And Documentation

**Files:**
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Optional Modify: `docs/experiment_startup_manual.md`

**Step 1: Inspect existing compose service**

Run:

```powershell
Get-Content -LiteralPath docker-compose.yml
```

Expected: find the `ai2thor` service and confirm where to add port guidance or a separate command.

**Step 2: Add observer usage docs**

Modify `README.md` with a section:

```markdown
## Run Realtime Browser Observer

Start the observer server in Docker:

```powershell
docker compose run --rm -p 8000:8000 ai2thor xvfb-run -a python scripts/run_observer_server.py --platform linux64 --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
```
```

If adding a compose profile is cleaner, add `ai2thor-observer` with `ports: ["8000:8000"]` and the same `xvfb-run` command.

**Step 3: Run documentation-adjacent smoke checks**

Run:

```powershell
python -m unittest tests.test_episode_observer tests.test_frame_encoding tests.test_web_observer tests.test_observer_server_import tests.test_observer_static_files -v
```

Expected: PASS.

**Step 4: Commit**

```powershell
git add README.md docker-compose.yml docs/experiment_startup_manual.md
git commit -m "docs: add realtime observer usage"
```

### Task 7: Final Verification

**Files:**
- No planned edits.

**Step 1: Run full test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Import server dependencies**

Run:

```powershell
python -c "from scripts.run_observer_server import create_app; print('observer import ok')"
```

Expected: `observer import ok`.

**Step 3: Optional Docker smoke**

Run only if Docker/AI2-THOR runtime time is acceptable:

```powershell
docker compose run --rm -p 8000:8000 ai2thor timeout 180s xvfb-run -a python scripts/run_observer_server.py --platform linux64 --host 0.0.0.0 --port 8000 --max-steps 3
```

Expected: server starts, browser can connect to `http://localhost:8000`, and logs show an episode starts. This may need manual interruption after visual confirmation.

**Step 4: Review git state**

Run:

```powershell
git status --short
```

Expected: clean working tree except for any intentionally uncommitted runtime output.
