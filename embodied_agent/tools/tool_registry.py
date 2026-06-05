from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from embodied_agent.schemas.data_models import ToolCall, ToolResult


@dataclass
class ToolSpec:
    name: str
    function: Callable[..., ToolResult]
    description: str
    args_schema: dict[str, Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.history: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        function: Callable[..., ToolResult],
        description: str = "",
        args_schema: dict[str, Any] | None = None,
    ) -> None:
        self._tools[name] = ToolSpec(name, function, description, args_schema or {})

    def execute(self, tool_call: ToolCall) -> ToolResult:
        spec = self._tools.get(tool_call.tool_name)
        if spec is None:
            result = ToolResult(False, f"Tool not found: {tool_call.tool_name}", {"failure_type": "unknown_tool"})
            self._record(tool_call, result)
            return result

        try:
            self._validate_args(spec, tool_call.args)
            result = spec.function(**tool_call.args)
            if not isinstance(result, ToolResult):
                result = ToolResult(False, "Tool did not return ToolResult", {"failure_type": "invalid_tool_result"})
        except (TypeError, ValueError) as exc:
            result = ToolResult(False, str(exc), {"failure_type": "bad_arguments"})
        except Exception as exc:
            result = ToolResult(False, str(exc), {"failure_type": "tool_exception"})

        self._record(tool_call, result)
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": spec.name, "description": spec.description, "args_schema": spec.args_schema}
            for spec in self._tools.values()
        ]

    def _validate_args(self, spec: ToolSpec, args: dict[str, Any]) -> None:
        inspect.signature(spec.function).bind(**args)
        for name, expected_type in spec.args_schema.items():
            if name in args and isinstance(expected_type, type) and not isinstance(args[name], expected_type):
                raise ValueError(f"Argument `{name}` must be {expected_type.__name__}")

    def _record(self, tool_call: ToolCall, result: ToolResult) -> None:
        self.history.append({"tool_call": tool_call, "result": result})
