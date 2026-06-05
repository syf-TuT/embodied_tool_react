from __future__ import annotations

import hashlib
from typing import Any

from embodied_agent.planners.base_planner import BasePlanner
from embodied_agent.schemas.data_models import Plan, SubTask, ToolCall


class RuleBasedPlanner(BasePlanner):
    def generate_plan(self, instruction: str, scene: str, observation: dict[str, Any]) -> Plan:
        normalized = instruction.lower().strip()
        task_id = self._task_id(instruction, scene)
        if normalized == "pick up the mug":
            subtasks = [
                self._subtask(
                    "s1",
                    "pick up the mug",
                    "Mug",
                    None,
                    "object_in_inventory:Mug",
                    [
                        ToolCall("search_object", {"object_type": "Mug"}, "Find the mug"),
                        ToolCall("pick_object", {"object_type": "Mug"}, "Pick up the mug"),
                    ],
                )
            ]
        elif normalized == "put the mug on the countertop":
            subtasks = [
                self._subtask(
                    "s1",
                    "put the mug on the countertop",
                    "Mug",
                    "CounterTop",
                    "object_on_receptacle:Mug:CounterTop",
                    [
                        ToolCall("search_object", {"object_type": "Mug"}, "Find the mug"),
                        ToolCall("pick_object", {"object_type": "Mug"}, "Pick up the mug"),
                        ToolCall("search_object", {"object_type": "CounterTop"}, "Find the countertop"),
                        ToolCall("put_object", {"receptacle_type": "CounterTop"}, "Place the mug"),
                    ],
                )
            ]
        elif normalized == "open the fridge":
            subtasks = [
                self._subtask(
                    "s1",
                    "open the fridge",
                    "Fridge",
                    None,
                    "object_open:Fridge",
                    [
                        ToolCall("search_object", {"object_type": "Fridge"}, "Find the fridge"),
                        ToolCall("open_object", {"object_type": "Fridge"}, "Open the fridge"),
                    ],
                )
            ]
        elif normalized == "put the apple in the fridge":
            subtasks = [
                self._subtask(
                    "s1",
                    "put the apple in the fridge",
                    "Apple",
                    "Fridge",
                    "object_on_receptacle:Apple:Fridge",
                    [
                        ToolCall("search_object", {"object_type": "Apple"}, "Find the apple"),
                        ToolCall("pick_object", {"object_type": "Apple"}, "Pick up the apple"),
                        ToolCall("search_object", {"object_type": "Fridge"}, "Find the fridge"),
                        ToolCall("open_object", {"object_type": "Fridge"}, "Open the fridge"),
                        ToolCall("put_object", {"receptacle_type": "Fridge"}, "Place the apple"),
                    ],
                )
            ]
        else:
            subtasks = [self._subtask("s1", f"unsupported instruction: {instruction}", None, None, "unsupported", [])]
        return Plan(task_id=task_id, instruction=instruction, subtasks=subtasks)

    def replan(
        self,
        instruction: str,
        failed_subtask: SubTask,
        failure_info: dict[str, Any],
        observation: dict[str, Any],
    ) -> list[SubTask]:
        return []

    def _subtask(
        self,
        subtask_id: str,
        description: str,
        target_object: str | None,
        target_receptacle: str | None,
        success_condition: str,
        tool_calls: list[ToolCall],
    ) -> SubTask:
        return SubTask(subtask_id, description, target_object, target_receptacle, success_condition, tool_calls)

    def _task_id(self, instruction: str, scene: str) -> str:
        digest = hashlib.md5(f"{scene}:{instruction}".encode("utf-8")).hexdigest()[:8]
        return f"task_{digest}"
