from __future__ import annotations

import csv
import json
from pathlib import Path

from embodied_agent.evaluation.metrics import compute_metrics


class ExperimentLogger:
    def __init__(self, output_dir: str | Path = "outputs") -> None:
        self.output_dir = Path(output_dir)
        self.trajectory_dir = self.output_dir / "trajectories"
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)

    def save_episode(self, result) -> None:
        path = self.trajectory_dir / f"{result.task_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    def save_summary(self, results) -> None:
        results = list(results)
        summary_path = self.output_dir / "summary.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "task_id",
                    "instruction",
                    "scene",
                    "success",
                    "total_steps",
                    "tool_call_count",
                    "invalid_action_count",
                    "replan_count",
                    "subtask_success_rate",
                ],
            )
            writer.writeheader()
            for item in results:
                data = item.to_dict()
                writer.writerow({field: data[field] for field in writer.fieldnames})

    def save_metrics(self, results) -> dict:
        metrics = compute_metrics(results)
        path = self.output_dir / "metrics.json"
        path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics
