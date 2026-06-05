import unittest

from embodied_agent.schemas.data_models import ToolCall, ToolResult
from embodied_agent.tools.tool_registry import ToolRegistry


class ToolRegistryTest(unittest.TestCase):
    def test_execute_registered_tool_returns_result_and_records_history(self) -> None:
        registry = ToolRegistry()

        def echo_tool(text: str) -> ToolResult:
            return ToolResult(success=True, message="ok", data={"text": text})

        registry.register("echo", echo_tool, "Echo text", {"text": str})

        result = registry.execute(ToolCall(tool_name="echo", args={"text": "hello"}))

        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "hello")
        self.assertEqual(len(registry.history), 1)
        self.assertEqual(registry.history[0]["tool_call"].tool_name, "echo")

    def test_missing_tool_returns_failure(self) -> None:
        registry = ToolRegistry()

        result = registry.execute(ToolCall(tool_name="missing", args={}))

        self.assertFalse(result.success)
        self.assertEqual(result.data["failure_type"], "unknown_tool")

    def test_bad_arguments_return_failure(self) -> None:
        registry = ToolRegistry()

        def needs_name(name: str) -> ToolResult:
            return ToolResult(success=True, message=name)

        registry.register("needs_name", needs_name, "Needs a name", {"name": str})

        result = registry.execute(ToolCall(tool_name="needs_name", args={}))

        self.assertFalse(result.success)
        self.assertEqual(result.data["failure_type"], "bad_arguments")


if __name__ == "__main__":
    unittest.main()
