import asyncio
import threading
import unittest

from embodied_agent.observers.web import WebObserver


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent = []
        self.sent_event = asyncio.Event()

    async def accept(self):
        self.accepted = True

    async def send_json(self, event):
        self.sent.append(event)
        self.sent_event.set()


class RaisingWebSocket(FakeWebSocket):
    async def send_json(self, event):
        raise RuntimeError("stale websocket")


class BlockingWebSocket(FakeWebSocket):
    async def send_json(self, event):
        await asyncio.sleep(10)


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


class WebObserverBroadcastTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)
        self.tasks = []

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.wait(self.tasks, timeout=0.2)

    def start_broadcast_loop(self, observer):
        task = asyncio.create_task(observer.broadcast_loop())
        self.tasks.append(task)
        return task

    async def test_connect_accepts_adds_broadcasts_and_disconnect_removes(self):
        observer = WebObserver()
        websocket = FakeWebSocket()

        await observer.connect(websocket)
        self.start_broadcast_loop(observer)
        observer.on_event({"type": "step"})
        await asyncio.wait_for(websocket.sent_event.wait(), timeout=0.2)
        observer.disconnect(websocket)

        self.assertTrue(websocket.accepted)
        self.assertNotIn(websocket, observer.clients)
        self.assertEqual(websocket.sent[0]["type"], "step")
        self.assertEqual(websocket.sent[0]["sequence"], 1)

    async def test_stale_or_slow_client_does_not_block_healthy_clients(self):
        observer = WebObserver(send_timeout=0.01)
        stale = RaisingWebSocket()
        slow = BlockingWebSocket()
        healthy = FakeWebSocket()

        await observer.connect(stale)
        await observer.connect(slow)
        await observer.connect(healthy)
        self.start_broadcast_loop(observer)
        observer.on_event({"type": "episode_end"})

        await asyncio.wait_for(healthy.sent_event.wait(), timeout=0.2)
        await asyncio.sleep(0.03)

        self.assertEqual(healthy.sent[0]["type"], "episode_end")
        self.assertNotIn(stale, observer.clients)
        self.assertNotIn(slow, observer.clients)
        self.assertIn(healthy, observer.clients)

    async def test_on_event_from_thread_wakes_broadcast_loop(self):
        observer = WebObserver()
        websocket = FakeWebSocket()

        await observer.connect(websocket)
        self.start_broadcast_loop(observer)
        await asyncio.sleep(0)
        self.assertIs(observer._loop, asyncio.get_running_loop())

        producer_error = []

        def produce_event():
            try:
                observer.on_event({"type": "thread_event"})
            except Exception as exc:
                producer_error.append(exc)

        producer = threading.Thread(target=produce_event)
        producer.start()
        producer.join(timeout=1)

        self.assertEqual(producer_error, [])
        await asyncio.wait_for(websocket.sent_event.wait(), timeout=0.2)
        self.assertEqual(websocket.sent[0]["type"], "thread_event")


if __name__ == "__main__":
    unittest.main()
