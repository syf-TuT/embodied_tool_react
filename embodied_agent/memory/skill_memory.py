from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillMemory:
    def __init__(self, path: str | Path = "outputs/skill_memory.json") -> None:
        self.path = Path(path)
        self.records: list[dict[str, Any]] = self._load()

    def add_failure_experience(
        self,
        task_instruction: str,
        scene: str,
        failed_subtask: dict[str, Any],
        failed_tool: dict[str, Any],
        failure_type: str,
        repair_strategy: str,
        final_success: bool,
    ) -> None:
        self.records.append(
            {
                "task_instruction": task_instruction,
                "scene": scene,
                "failed_subtask": failed_subtask,
                "failed_tool": failed_tool,
                "failure_type": failure_type,
                "repair_strategy": repair_strategy,
                "final_success": final_success,
            }
        )
        self.save()

    def retrieve_similar(self, task_instruction: str) -> list[dict[str, Any]]:
        keywords = {token for token in task_instruction.lower().split() if len(token) > 2}
        scored = []
        for record in self.records:
            text = record.get("task_instruction", "").lower()
            score = sum(1 for token in keywords if token in text)
            if score:
                scored.append((score, record))
        return [record for _, record in sorted(scored, key=lambda item: item[0], reverse=True)]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))
