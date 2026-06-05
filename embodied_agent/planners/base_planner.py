from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from embodied_agent.schemas.data_models import Plan, SubTask


class BasePlanner(ABC):
    @abstractmethod
    def generate_plan(self, instruction: str, scene: str, observation: dict[str, Any]) -> Plan:
        raise NotImplementedError

    @abstractmethod
    def replan(
        self,
        instruction: str,
        failed_subtask: SubTask,
        failure_info: dict[str, Any],
        observation: dict[str, Any],
    ) -> list[SubTask]:
        raise NotImplementedError
