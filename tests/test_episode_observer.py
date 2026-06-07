import unittest

from embodied_agent.factory import build_default_tool_registry
from embodied_agent.planners import RuleBasedPlanner
from embodied_agent.runner import EpisodeRunner
from embodied_agent.schemas.data_models import Plan, ToolResult


class RecordingObserver:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


class ObserverEnv:
    def __init__(self):
        self.agent_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.inventory = []
        self.objects = [
            {
                "objectId": "Mug|1",
                "objectType": "Mug",
                "visible": True,
                "pickupable": True,
                "position": {"x": 0.5, "y": 0.9, "z": 0.0},
                "distance": 0.5,
            }
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

    def get_agent_state(self):
        return {"position": self.agent_position}

    def get_frame(self):
        return None

    def step(self, action, **kwargs):
        if action == "PickupObject":
            self.inventory = [{"objectId": "Mug|1", "objectType": "Mug"}]
            self.objects[0]["visible"] = False
            return ToolResult(True, "picked", observation={"metadata": self.get_metadata()})
        return ToolResult(True, "ok", observation={"metadata": self.get_metadata()})


class NoObserverStateEnv:
    def reset(self, scene):
        return ToolResult(True, "reset_success", observation={"metadata": {}})

    def get_visible_objects(self):
        raise AssertionError("observer-only visible object state should not be read")

    def get_agent_state(self):
        raise AssertionError("observer-only agent state should not be read")


class EmptyPlanner:
    def generate_plan(self, instruction, scene, observation):
        return Plan("generated_task", instruction, [])


class EpisodeObserverTest(unittest.TestCase):
    def test_runner_emits_episode_step_and_end_events(self):
        observer = RecordingObserver()
        env = ObserverEnv()
        runner = EpisodeRunner(
            env,
            RuleBasedPlanner(),
            build_default_tool_registry(env),
            max_steps=10,
            observer=observer,
        )

        result = runner.run("task_observe", "pick up the mug", "FloorPlan1")

        event_types = [event["type"] for event in observer.events]
        self.assertTrue(result.success)
        self.assertEqual(event_types[0], "episode_start")
        self.assertIn("step", event_types)
        self.assertEqual(event_types[-1], "episode_end")
        self.assertEqual(observer.events[0]["task_id"], "task_observe")
        self.assertIn("visible_objects", observer.events[0])
        self.assertIn("agent", observer.events[0])
        step_event = next(
            event
            for event in observer.events
            if event["type"] == "step" and event["tool_name"] == "pick_object"
        )
        self.assertEqual(step_event["tool_name"], "pick_object")
        self.assertEqual(step_event["task_id"], "task_observe")
        self.assertIn("visible_objects", step_event)
        self.assertIn("agent", step_event)
        self.assertEqual(observer.events[-1]["task_id"], "task_observe")
        self.assertIn("visible_objects", observer.events[-1])
        self.assertIn("agent", observer.events[-1])

    def test_no_observer_skips_observer_state_reads(self):
        env = NoObserverStateEnv()
        runner = EpisodeRunner(
            env,
            EmptyPlanner(),
            build_default_tool_registry(env),
            observer=None,
        )

        result = runner.run("task_no_observer", "already done", "FloorPlan1")

        self.assertTrue(result.success)
        self.assertEqual(result.task_id, "task_no_observer")


if __name__ == "__main__":
    unittest.main()
