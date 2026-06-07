import importlib.util
import io
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest import mock


class ObserverServerImportTest(unittest.TestCase):
    def load_module(self):
        path = Path("scripts/run_observer_server.py")
        spec = importlib.util.spec_from_file_location("run_observer_server", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_server_script_imports_expected_symbols(self):
        module = self.load_module()

        self.assertTrue(hasattr(module, "create_app"))
        self.assertTrue(hasattr(module, "main"))
        self.assertTrue(hasattr(module, "parse_args"))
        self.assertTrue(hasattr(module, "FrameWebObserver"))
        self.assertTrue(hasattr(module, "format_missing_dependency_message"))

    def test_import_and_parse_args_do_not_instantiate_ai2thor_env(self):
        with mock.patch("embodied_agent.envs.AI2ThorEnv") as ai2thor_env:
            module = self.load_module()
            args = module.parse_args([])

        self.assertEqual(args.scene, "FloorPlan1")
        ai2thor_env.assert_not_called()

    def test_run_episode_wrapper_emits_observer_error_event(self):
        module = self.load_module()
        observer = mock.Mock()
        stderr = io.StringIO()

        with mock.patch.object(
            module, "start_episode", side_effect=ValueError("boom")
        ), mock.patch("sys.stderr", stderr):
            module.run_episode_with_error_event(SimpleNamespace(), observer)

        observer.on_event.assert_called_once_with(
            {
                "type": "observer_error",
                "message": "boom",
                "error_type": "ValueError",
            }
        )
        self.assertIn("ValueError: boom", stderr.getvalue())

    def test_ensure_runner_thread_reuses_alive_thread_and_replaces_stopped_thread(self):
        module = self.load_module()
        state = SimpleNamespace()
        started = []

        class FakeThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon
                self.alive = False

            def start(self):
                self.alive = True
                started.append(self)

            def is_alive(self):
                return self.alive

        first = module.ensure_runner_thread(
            state, SimpleNamespace(), mock.Mock(), thread_factory=FakeThread
        )
        second = module.ensure_runner_thread(
            state, SimpleNamespace(), mock.Mock(), thread_factory=FakeThread
        )
        first.alive = False
        third = module.ensure_runner_thread(
            state, SimpleNamespace(), mock.Mock(), thread_factory=FakeThread
        )

        self.assertIs(first, second)
        self.assertIsNot(first, third)
        self.assertEqual(started, [first, third])

    def test_missing_dependency_message_names_requirements_install(self):
        module = self.load_module()

        message = module.format_missing_dependency_message(
            ModuleNotFoundError("No module named 'fastapi'")
        )

        self.assertIn("Missing Python dependency", message)
        self.assertIn("pip install -r requirements.txt", message)


if __name__ == "__main__":
    unittest.main()
