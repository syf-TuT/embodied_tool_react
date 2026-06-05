from __future__ import annotations

import argparse
import json
from pathlib import Path

from embodied_agent.envs import AI2ThorEnv
from embodied_agent.evaluation.logger import ExperimentLogger
from embodied_agent.factory import build_default_tool_registry
from embodied_agent.memory import SkillMemory
from embodied_agent.planners import MockLLMPlanner, RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner


def load_config(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml

        return yaml.safe_load(text)
    except ImportError:
        config = {}
        for line in text.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            key, value = line.split(":", 1)
            config[key.strip()] = _parse_scalar(value.strip())
        return config


def _parse_scalar(value: str):
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def build_planner(planner_type: str):
    if planner_type == "mock_llm":
        return MockLLMPlanner()
    return RuleBasedPlanner()


def run_tasks(config_path: str, tasks_path: str) -> list:
    config = load_config(config_path)
    tasks = json.loads(Path(tasks_path).read_text(encoding="utf-8"))
    env = AI2ThorEnv(
        scene=config.get("scene", "FloorPlan1"),
        grid_size=float(config.get("grid_size", 0.25)),
        visibility_distance=float(config.get("visibility_distance", 1.5)),
    )
    registry = build_default_tool_registry(env)
    planner = build_planner(config.get("planner_type", "rule_based"))
    output_dir = config.get("output_dir", "outputs")
    runner = EpisodeRunner(
        env=env,
        planner=planner,
        tool_registry=registry,
        max_steps=int(config.get("max_steps", 50)),
        max_replans=int(config.get("max_replans", 3)),
        memory=SkillMemory(Path(output_dir) / "skill_memory.json"),
    )
    logger = ExperimentLogger(output_dir)
    results = []
    for task in tasks:
        result = runner.run(task["task_id"], task["instruction"], task.get("scene", config.get("scene", "FloorPlan1")))
        logger.save_episode(result)
        results.append(result)
    logger.save_summary(results)
    logger.save_metrics(results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tasks", default="configs/tasks_ai2thor.json")
    args = parser.parse_args()
    results = run_tasks(args.config, args.tasks)
    print(f"Finished {len(results)} tasks")


if __name__ == "__main__":
    main()
