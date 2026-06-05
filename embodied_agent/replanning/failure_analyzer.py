from __future__ import annotations

from typing import Any

from embodied_agent.schemas.data_models import SubTask, ToolCall, ToolResult


class FailureAnalyzer:
    def analyze(
        self,
        failed_tool_call: ToolCall,
        tool_result: ToolResult,
        subtask: SubTask | None,
        env_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        failure_type = tool_result.data.get("failure_type") or self._infer_failure_type(failed_tool_call, tool_result)
        repair_strategy = self._repair_strategy(failed_tool_call, failure_type)
        return {
            "failure_type": failure_type,
            "possible_reason": tool_result.message or failure_type,
            "repair_strategy": repair_strategy,
            "failed_tool": failed_tool_call.to_dict(),
            "subtask_id": getattr(subtask, "subtask_id", None),
        }

    def _infer_failure_type(self, failed_tool_call: ToolCall, tool_result: ToolResult) -> str:
        message = tool_result.message.lower()
        if "not_visible" in message or "not visible" in message:
            return "object_not_visible"
        if "not_pickupable" in message or "pickupable" in message:
            return "object_not_pickupable"
        if "not_openable" in message or "openable" in message:
            return "object_not_openable"
        if failed_tool_call.tool_name == "put_object" and "fridge" in str(failed_tool_call.args).lower():
            return "precondition_missing"
        if "wrong_receptacle" in message:
            return "wrong_receptacle"
        if "precondition" in message:
            return "precondition_missing"
        if tool_result.data.get("lastActionSuccess") is False:
            return "action_failed"
        return "unknown_failure"

    def _repair_strategy(self, failed_tool_call: ToolCall, failure_type: str) -> str:
        if failure_type == "object_not_visible":
            return "search_object"
        if failure_type == "precondition_missing":
            target = failed_tool_call.args.get("receptacle_type") or failed_tool_call.args.get("object_type")
            if str(target).lower() in {"fridge", "cabinet", "drawer"}:
                return "open_object"
        if failure_type == "action_failed":
            return "retry"
        return "abort"
