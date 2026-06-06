import unittest

from embodied_agent.envs.ai2thor_env import AI2ThorEnv


class FakeController:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class AI2ThorEnvTest(unittest.TestCase):
    def test_stop_stops_underlying_controller(self) -> None:
        env = AI2ThorEnv.__new__(AI2ThorEnv)
        env.controller = FakeController()

        env.stop()

        self.assertTrue(env.controller.stopped)


if __name__ == "__main__":
    unittest.main()
