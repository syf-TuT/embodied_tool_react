from __future__ import annotations

from typing import Any

from embodied_agent.schemas.data_models import ToolCall


class Replanner:
    def __init__(self, max_replans: int = 3) -> None:
        self.max_replans = max_replans
        self.history: list[dict[str, Any]] = []

    def repair_calls(
        self,
        failed_tool_call: ToolCall,
        failure_info: dict[str, Any],
        current_replan_count: int,
    ) -> list[ToolCall]:
        if current_replan_count >= self.max_replans:
            return []

        failure_type = failure_info.get("failure_type")
        calls: list[ToolCall] = []
        if failure_type == "object_not_visible":
            object_type = failed_tool_call.args.get("object_type") or failed_tool_call.args.get("receptacle_type")
            if object_type:
                calls.append(ToolCall("search_object", {"object_type": object_type}, "Repair: search for missing object"))
        elif failure_type == "precondition_missing":
            target = failed_tool_call.args.get("receptacle_type") or failed_tool_call.args.get("object_type")
            if str(target).lower() in {"fridge", "cabinet", "drawer"}:
                calls.append(ToolCall("open_object", {"object_type": target}, "Repair: open container"))
        elif failure_type == "action_failed":
            calls.append(failed_tool_call)

        self.history.append({"failure_info": failure_info, "repair_calls": [call.to_dict() for call in calls]})
        return calls
