import importlib.util
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

    def test_import_and_parse_args_do_not_instantiate_ai2thor_env(self):
        with mock.patch("embodied_agent.envs.AI2ThorEnv") as ai2thor_env:
            module = self.load_module()
            args = module.parse_args([])

        self.assertEqual(args.scene, "FloorPlan1")
        ai2thor_env.assert_not_called()


if __name__ == "__main__":
    unittest.main()
