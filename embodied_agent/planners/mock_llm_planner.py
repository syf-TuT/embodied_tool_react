from __future__ import annotations

import json
from typing import Any

from embodied_agent.planners.rule_based_planner import RuleBasedPlanner
from embodied_agent.schemas.data_models import Plan, SubTask, ToolCall


class MockLLMPlanner(RuleBasedPlanner):
    """Mimics an LLM JSON plan while reusing deterministic templates."""

    def generate_plan(self, instruction: str, scene: str, observation: dict[str, Any]) -> Plan:
        base_plan = super().generate_plan(instruction, scene, observation)
        payload = json.loads(json.dumps(base_plan.to_dict()))
        subtasks = [
            SubTask(
                subtask_id=item["subtask_id"],
                description=item["description"],
                target_object=item["target_object"],
                target_receptacle=item["target_receptacle"],
                success_condition=item["success_condition"],
                tool_calls=[ToolCall(**call) for call in item["tool_calls"]],
            )
            for item in payload["subtasks"]
        ]
        return Plan(task_id=payload["task_id"], instruction=payload["instruction"], subtasks=subtasks)
