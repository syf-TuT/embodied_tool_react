from __future__ import annotations

from embodied_agent.schemas.data_models import SubTask, ToolResult
from embodied_agent.tools.state_tools import (
    check_object_in_inventory,
    check_object_on_receptacle,
    check_object_open,
    check_object_visible,
)


class SuccessDetector:
    def check(self, subtask: SubTask, env) -> ToolResult:
        parts = subtask.success_condition.split(":")
        condition = parts[0]

        if condition == "object_visible" and len(parts) == 2:
            result = check_object_visible(env, parts[1])
        elif condition == "object_in_inventory" and len(parts) == 2:
            result = check_object_in_inventory(env, parts[1])
        elif condition == "object_on_receptacle" and len(parts) == 3:
            result = check_object_on_receptacle(env, parts[1], parts[2])
        elif condition == "object_open" and len(parts) == 2:
            result = check_object_open(env, parts[1])
        else:
            result = ToolResult(False, "unsupported_success_condition", {"condition": subtask.success_condition})

        evidence = dict(result.data)
        result.data.setdefault("reason", condition)
        result.data.setdefault("evidence", evidence)
        return result
