import unittest

from embodied_agent.replanning.failure_analyzer import FailureAnalyzer
from embodied_agent.schemas.data_models import SubTask, ToolCall, ToolResult


class FailureAnalyzerTest(unittest.TestCase):
    def test_pick_failure_when_object_not_visible_suggests_search(self) -> None:
        analyzer = FailureAnalyzer()
        failed_call = ToolCall(tool_name="pick_object", args={"object_type": "Mug"})
        result = ToolResult(
            success=False,
            message="object_not_visible",
            data={"failure_type": "object_not_visible"},
        )
        subtask = SubTask(
            subtask_id="s1",
            description="pick mug",
            target_object="Mug",
            target_receptacle=None,
            success_condition="object_in_inventory:Mug",
            tool_calls=[failed_call],
        )

        info = analyzer.analyze(failed_call, result, subtask, {"objects": []})

        self.assertEqual(info["failure_type"], "object_not_visible")
        self.assertEqual(info["repair_strategy"], "search_object")

    def test_put_failure_on_closed_fridge_suggests_open(self) -> None:
        analyzer = FailureAnalyzer()
        failed_call = ToolCall(tool_name="put_object", args={"receptacle_type": "Fridge"})
        result = ToolResult(success=False, message="precondition_missing")

        info = analyzer.analyze(failed_call, result, None, {"objects": []})

        self.assertEqual(info["failure_type"], "precondition_missing")
        self.assertEqual(info["repair_strategy"], "open_object")


if __name__ == "__main__":
    unittest.main()
