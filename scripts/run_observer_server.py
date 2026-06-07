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
    def __init__(self, env=None, send_timeout: float = 1.0) -> None:
        super().__init__(send_timeout=send_timeout)
        self.env = env

    def on_event(self, event):
        enriched = dict(event)
        try:
            enriched["frame"] = encode_frame_jpeg_data_url(self.env.get_frame())
        except Exception as exc:
            enriched["frame"] = None
            enriched["observer_warning"] = f"frame_encoding_failed: {exc}"
        super().on_event(enriched)


def build_controller_kwargs(args):
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
    return controller_kwargs


def start_episode(args, observer: FrameWebObserver) -> None:
    env = AI2ThorEnv(
        scene=args.scene,
        controller_kwargs=build_controller_kwargs(args),
    )
    observer.env = env
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
    observer = FrameWebObserver()
    app = create_observer_app(observer, ROOT / "web" / "observer")
    app.state.observer = observer
    app.state.runner_thread = threading.Thread(
        target=start_episode,
        args=(args, observer),
        daemon=True,
    )

    @app.on_event("startup")
    async def start_runner_thread() -> None:
        app.state.runner_thread.start()

    return app


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run AI2-THOR with a realtime browser observer."
    )
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
    parser.add_argument(
        "--platform",
        choices=["auto", "cloudrendering", "linux64"],
        default="auto",
        help="AI2-THOR runtime platform. CloudRendering is useful on Linux headless hosts.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def main() -> None:
    import uvicorn

    args = parse_args()
    uvicorn.run(create_app(args), host=args.host, port=args.port)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
