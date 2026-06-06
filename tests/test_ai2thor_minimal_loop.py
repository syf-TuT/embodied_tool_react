import unittest

from embodied_agent.factory import build_default_tool_registry
from embodied_agent.planners import RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner
from embodied_agent.schemas.data_models import ToolResult
from embodied_agent.tools.navigation_tools import make_search_object


class MinimalThorLikeEnv:
    def __init__(self, apple_visible=False, apple_distance=2.5, fail_first_put=False) -> None:
        self.agent_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.inventory = []
        self.fail_first_put = fail_first_put
        self.put_attempts = 0
        self.actions = []
        self.objects = [
            {
                "objectId": "Apple|1",
                "objectType": "Apple",
                "visible": apple_visible,
                "pickupable": True,
                "position": {"x": 2.0, "y": 0.9, "z": 0.0},
                "distance": apple_distance,
                "parentReceptacles": [],
            },
            {
                "objectId": "Fridge|1",
                "objectType": "Fridge",
                "visible": True,
                "openable": True,
                "receptacle": True,
                "isOpen": False,
                "position": {"x": 2.1, "y": 0.0, "z": 0.2},
                "distance": 2.6,
            },
        ]

    def reset(self, scene):
        return ToolResult(True, "reset_success", observation={"metadata": self.get_metadata()})

    def get_metadata(self):
        return {
            "objects": self.objects,
            "inventoryObjects": self.inventory,
            "agent": {"position": self.agent_position},
            "lastActionSuccess": True,
        }

    def get_objects(self):
        return self.objects

    def get_visible_objects(self):
        return [obj for obj in self.objects if obj.get("visible")]

    def get_inventory_objects(self):
        return self.inventory

    def get_reachable_positions(self):
        self.actions.append(("GetReachablePositions", {}))
        return [
            {"x": 0.0, "y": 0.0, "z": 0.0},
            {"x": 1.8, "y": 0.0, "z": 0.0},
            {"x": 2.0, "y": 0.0, "z": 0.2},
        ]

    def teleport(self, position, rotation=0.0, horizon=0.0):
        self.actions.append(("TeleportFull", {"position": position, "rotation": rotation, "horizon": horizon}))
        self.agent_position = dict(position)
        for obj in self.objects:
            obj["distance"] = abs(obj["position"]["x"] - position["x"]) + abs(obj["position"]["z"] - position["z"])
            if obj["distance"] <= 1.5:
                obj["visible"] = True
        return ToolResult(True, "teleport_success", observation={"metadata": self.get_metadata()})

    def step(self, action, **kwargs):
        self.actions.append((action, kwargs))
        if action == "RotateRight":
            return ToolResult(True, "rotated", observation={"metadata": self.get_metadata()})
        if action == "PickupObject":
            apple = self.objects[0]
            if apple["distance"] > 1.5:
                return ToolResult(False, "too_far", {"failure_type": "action_failed", "lastActionSuccess": False})
            self.inventory = [{"objectId": "Apple|1", "objectType": "Apple"}]
            apple["visible"] = False
            return ToolResult(True, "picked", observation={"metadata": self.get_metadata()})
        if action == "OpenObject":
            fridge = self.objects[1]
            if fridge["distance"] > 1.5:
                return ToolResult(False, "too_far", {"failure_type": "action_failed", "lastActionSuccess": False})
            fridge["isOpen"] = True
            return ToolResult(True, "opened", observation={"metadata": self.get_metadata()})
        if action == "PutObject":
            self.put_attempts += 1
            fridge = self.objects[1]
            if not fridge["isOpen"]:
                return ToolResult(False, "precondition_missing", {"failure_type": "precondition_missing"})
            if self.fail_first_put and self.put_attempts == 1:
                return ToolResult(False, "action_failed", {"failure_type": "action_failed", "lastActionSuccess": False})
            if fridge["distance"] > 1.5:
                return ToolResult(False, "too_far", {"failure_type": "action_failed", "lastActionSuccess": False})
            self.inventory = []
            self.objects[0]["parentReceptacles"] = ["Fridge|1"]
            return ToolResult(True, "put", observation={"metadata": self.get_metadata()})
        return ToolResult(False, "unknown", {"failure_type": "unknown_failure"})


class RealAi2ThorMinimalLoopTest(unittest.TestCase):
    def test_rule_based_ai2thor_plan_uses_bounded_search_budget(self) -> None:
        plan = RuleBasedPlanner().generate_plan("put the apple in the fridge", "FloorPlan1", {})
        search_calls = [
            call
            for subtask in plan.subtasks
            for call in subtask.tool_calls
            if call.tool_name == "search_object"
        ]

        self.assertEqual(len(search_calls), 2)
        for call in search_calls:
            self.assertLessEqual(call.args["max_rotations"], 1)
            self.assertLessEqual(call.args["max_positions"], 4)

    def test_search_object_uses_reachable_positions_and_teleport_when_target_not_visible(self) -> None:
        env = MinimalThorLikeEnv(apple_visible=False)
        result = make_search_object(env)("Apple", max_rotations=1, max_positions=3)

        self.assertTrue(result.success)
        self.assertIn("TeleportFull", [name for name, _ in env.actions])

    def test_put_apple_in_fridge_runs_with_navigation_retry_for_distance(self) -> None:
        env = MinimalThorLikeEnv(apple_visible=True, apple_distance=2.5)
        runner = EpisodeRunner(env, RuleBasedPlanner(), build_default_tool_registry(env), max_steps=30, max_replans=3)

        result = runner.run("task_real_minimal", "put the apple in the fridge", "FloorPlan1")

        self.assertTrue(result.success)
        self.assertIn("TeleportFull", [name for name, _ in env.actions])
        self.assertEqual(result.failure_reasons, [])

    def test_action_failed_replan_retries_put_once_without_duplicate_retry_pair(self) -> None:
        env = MinimalThorLikeEnv(apple_visible=True, apple_distance=0.5, fail_first_put=True)
        runner = EpisodeRunner(env, RuleBasedPlanner(), build_default_tool_registry(env), max_steps=30, max_replans=3)

        result = runner.run("task_retry", "put the apple in the fridge", "FloorPlan1")

        put_steps = [step for step in result.trajectory if step["tool_name"] == "put_object"]
        self.assertTrue(result.success)
        self.assertEqual(len(put_steps), 2)
        self.assertEqual(result.failure_reasons, ["action_failed"])


if __name__ == "__main__":
    unittest.main()
