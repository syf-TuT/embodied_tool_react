import unittest

from embodied_agent.observers.web import WebObserver


class WebObserverTest(unittest.TestCase):
    def test_on_event_enqueues_event_without_clients(self):
        observer = WebObserver()

        observer.on_event({"type": "step", "step_id": 1})
        event = observer.queue.get_nowait()

        self.assertEqual(event["type"], "step")
        self.assertEqual(event["step_id"], 1)

    def test_adds_sequence_number(self):
        observer = WebObserver()

        observer.on_event({"type": "episode_start"})
        observer.on_event({"type": "episode_end"})
        first = observer.queue.get_nowait()
        second = observer.queue.get_nowait()

        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)


if __name__ == "__main__":
    unittest.main()
