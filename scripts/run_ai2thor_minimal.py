from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from embodied_agent.envs import AI2ThorEnv
from embodied_agent.evaluation.logger import ExperimentLogger
from embodied_agent.factory import build_default_tool_registry
from embodied_agent.memory import SkillMemory
from embodied_agent.planners import RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one minimal AI2-THOR closed-loop task.")
    parser.add_argument("--scene", default="FloorPlan1")
    parser.add_argument("--instruction", default="put the apple in the fridge")
    parser.add_argument("--task-id", default="ai2thor_minimal_001")
    parser.add_argument("--output-dir", default="outputs/ai2thor_minimal")
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
    args = parser.parse_args()

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

    env = AI2ThorEnv(
        scene=args.scene,
        controller_kwargs=controller_kwargs,
    )
    try:
        registry = build_default_tool_registry(env)
        runner = EpisodeRunner(
            env=env,
            planner=RuleBasedPlanner(),
            tool_registry=registry,
            max_steps=args.max_steps,
            max_replans=args.max_replans,
            memory=SkillMemory(Path(args.output_dir) / "skill_memory.json"),
        )

        result = runner.run(args.task_id, args.instruction, args.scene)
        logger = ExperimentLogger(args.output_dir)
        logger.save_episode(result)
        logger.save_summary([result])
        metrics = logger.save_metrics([result])

        print(json.dumps(
            {
                "task_id": result.task_id,
                "scene": result.scene,
                "instruction": result.instruction,
                "success": result.success,
                "total_steps": result.total_steps,
                "replan_count": result.replan_count,
                "failure_reasons": result.failure_reasons,
                "metrics": metrics,
                "trajectory_path": str(Path(args.output_dir) / "trajectories" / f"{result.task_id}.json"),
            },
            indent=2,
        ))
    finally:
        env.stop()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
