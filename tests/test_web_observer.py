import asyncio
import queue
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


class EmitDuringReplayWebSocket(FakeWebSocket):
    def __init__(self, observer):
        super().__init__()
        self.observer = observer
        self.emitted = False

    async def send_json(self, event):
        await super().send_json(event)
        if event["type"] == "episode_start" and not self.emitted:
            self.emitted = True
            self.observer.on_event({"type": "during_connect"})
            await wait_until(self.observer.queue.empty)


class EmitLiveAfterFirstHistoryWebSocket(FakeWebSocket):
    def __init__(self, observer):
        super().__init__()
        self.observer = observer
        self.emitted = False

    async def send_json(self, event):
        await super().send_json(event)
        if event["type"] == "history_1" and not self.emitted:
            self.emitted = True
            self.observer.on_event({"type": "live_3"})
            await wait_until(self.observer.queue.empty)
            if self in self.observer.clients:
                await asyncio.wait_for(
                    self.observer.live_send_started.wait(), timeout=0.2
                )


class LiveSendTrackingObserver(WebObserver):
    def __init__(self):
        super().__init__()
        self.live_send_started = asyncio.Event()

    async def _send_to_client(self, client, event):
        if event["type"] == "live_3":
            self.live_send_started.set()
        return await super()._send_to_client(client, event)


async def wait_until(predicate, timeout=0.5, interval=0.005):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(interval)
    return True


class WebObserverTest(unittest.TestCase):
    def test_uses_thread_safe_standard_queue(self):
        observer = WebObserver()

        self.assertIsInstance(observer.queue, queue.Queue)

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
        cleanup_finished = await wait_until(
            lambda: stale not in observer.clients and slow not in observer.clients
        )

        self.assertEqual(healthy.sent[0]["type"], "episode_end")
        self.assertTrue(cleanup_finished)
        self.assertNotIn(stale, observer.clients)
        self.assertNotIn(slow, observer.clients)
        self.assertIn(healthy, observer.clients)

    async def test_on_event_from_thread_wakes_broadcast_loop(self):
        observer = WebObserver()
        websocket = FakeWebSocket()

        await observer.connect(websocket)
        self.start_broadcast_loop(observer)
        await asyncio.sleep(0)

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

    async def test_on_event_from_thread_before_broadcast_loop_delivers_later(self):
        observer = WebObserver()
        websocket = FakeWebSocket()
        producer_error = []

        def produce_event():
            try:
                observer.on_event({"type": "early_thread_event"})
            except Exception as exc:
                producer_error.append(exc)

        producer = threading.Thread(target=produce_event)
        producer.start()
        producer.join(timeout=1)

        await observer.connect(websocket)
        self.start_broadcast_loop(observer)

        self.assertEqual(producer_error, [])
        await asyncio.wait_for(websocket.sent_event.wait(), timeout=0.2)
        self.assertEqual(websocket.sent[0]["type"], "early_thread_event")

    async def test_replays_recent_events_to_client_after_queue_was_drained(self):
        observer = WebObserver()
        self.start_broadcast_loop(observer)

        observer.on_event({"type": "episode_start"})
        observer.on_event({"type": "step", "step_id": 1})
        queue_drained = await wait_until(observer.queue.empty)

        websocket = FakeWebSocket()
        await observer.connect(websocket)

        self.assertTrue(queue_drained)
        await asyncio.wait_for(websocket.sent_event.wait(), timeout=0.2)
        self.assertEqual(
            [event["type"] for event in websocket.sent],
            ["episode_start", "step"],
        )

    async def test_event_emitted_during_replay_is_delivered_once(self):
        observer = WebObserver()
        self.start_broadcast_loop(observer)
        observer.on_event({"type": "episode_start"})
        history_drained = await wait_until(observer.queue.empty)

        websocket = EmitDuringReplayWebSocket(observer)
        await observer.connect(websocket)
        delivered = await wait_until(lambda: len(websocket.sent) == 2)

        self.assertTrue(history_drained)
        self.assertTrue(delivered)
        self.assertEqual(
            [event["type"] for event in websocket.sent],
            ["episode_start", "during_connect"],
        )

    async def test_live_event_during_replay_does_not_skip_remaining_history(self):
        observer = LiveSendTrackingObserver()
        self.start_broadcast_loop(observer)
        observer.on_event({"type": "history_1"})
        observer.on_event({"type": "history_2"})
        history_drained = await wait_until(observer.queue.empty)

        websocket = EmitLiveAfterFirstHistoryWebSocket(observer)
        await observer.connect(websocket)
        delivered = await wait_until(lambda: len(websocket.sent) == 3)

        self.assertTrue(history_drained)
        self.assertTrue(delivered)
        self.assertEqual(
            [event["type"] for event in websocket.sent],
            ["history_1", "history_2", "live_3"],
        )


if __name__ == "__main__":
    unittest.main()
