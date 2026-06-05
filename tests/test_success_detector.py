import unittest

from embodied_agent.detectors.success_detector import SuccessDetector
from embodied_agent.schemas.data_models import SubTask


class FakeEnv:
    def __init__(self) -> None:
        self.objects = [
            {
                "objectId": "Mug|1",
                "objectType": "Mug",
                "visible": True,
                "parentReceptacles": ["CounterTop|1"],
            },
            {
                "objectId": "CounterTop|1",
                "objectType": "CounterTop",
                "visible": True,
            },
            {"objectId": "Fridge|1", "objectType": "Fridge", "isOpen": True},
        ]
        self.inventory = [{"objectId": "Apple|1", "objectType": "Apple"}]

    def get_objects(self):
        return self.objects

    def get_visible_objects(self):
        return [obj for obj in self.objects if obj.get("visible")]

    def get_inventory_objects(self):
        return self.inventory


class SuccessDetectorTest(unittest.TestCase):
    def test_detects_inventory_condition(self) -> None:
        subtask = SubTask(
            subtask_id="s1",
            description="pick apple",
            target_object="Apple",
            target_receptacle=None,
            success_condition="object_in_inventory:Apple",
            tool_calls=[],
        )

        result = SuccessDetector().check(subtask, FakeEnv())

        self.assertTrue(result.success)
        self.assertEqual(result.data["reason"], "object_in_inventory")

    def test_detects_object_on_receptacle_condition(self) -> None:
        subtask = SubTask(
            subtask_id="s2",
            description="put mug",
            target_object="Mug",
            target_receptacle="CounterTop",
            success_condition="object_on_receptacle:Mug:CounterTop",
            tool_calls=[],
        )

        result = SuccessDetector().check(subtask, FakeEnv())

        self.assertTrue(result.success)
        self.assertTrue(result.data["evidence"]["matched"])


if __name__ == "__main__":
    unittest.main()
