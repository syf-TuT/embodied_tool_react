from __future__ import annotations

from collections import Counter


def compute_metrics(results) -> dict:
    results = list(results)
    if not results:
        return {
            "task_success_rate": 0.0,
            "average_steps": 0.0,
            "average_tool_calls": 0.0,
            "average_replans": 0.0,
            "invalid_action_rate": 0.0,
            "subtask_success_rate": 0.0,
            "failure_type_distribution": {},
        }

    total = len(results)
    total_tool_calls = sum(item.tool_call_count for item in results)
    failures = Counter(reason for item in results for reason in item.failure_reasons)
    return {
        "task_success_rate": sum(1 for item in results if item.success) / total,
        "average_steps": sum(item.total_steps for item in results) / total,
        "average_tool_calls": total_tool_calls / total,
        "average_replans": sum(item.replan_count for item in results) / total,
        "invalid_action_rate": sum(item.invalid_action_count for item in results) / total_tool_calls if total_tool_calls else 0.0,
        "subtask_success_rate": sum(item.subtask_success_rate for item in results) / total,
        "failure_type_distribution": dict(failures),
    }
