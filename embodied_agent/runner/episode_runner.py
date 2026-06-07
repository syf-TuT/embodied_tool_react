from __future__ import annotations

from typing import Any

from embodied_agent.detectors.success_detector import SuccessDetector
from embodied_agent.memory.skill_memory import SkillMemory
from embodied_agent.observers import EpisodeObserver
from embodied_agent.replanning.failure_analyzer import FailureAnalyzer
from embodied_agent.replanning.replanner import Replanner
from embodied_agent.schemas.data_models import EpisodeResult, ToolCall


class EpisodeRunner:
    def __init__(
        self,
        env,
        planner,
        tool_registry,
        max_steps: int = 50,
        max_replans: int = 3,
        success_detector: SuccessDetector | None = None,
        failure_analyzer: FailureAnalyzer | None = None,
        replanner: Replanner | None = None,
        memory: SkillMemory | None = None,
        observer: EpisodeObserver | None = None,
    ) -> None:
        self.env = env
        self.planner = planner
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.max_replans = max_replans
        self.success_detector = success_detector or SuccessDetector()
        self.failure_analyzer = failure_analyzer or FailureAnalyzer()
        self.replanner = replanner or Replanner(max_replans=max_replans)
        self.memory = memory
        self.observer = observer

    def run(self, task_id: str, instruction: str, scene: str) -> EpisodeResult:
        reset_result = self.env.reset(scene)
        plan = self.planner.generate_plan(instruction, scene, reset_result.observation)
        plan.task_id = task_id or plan.task_id
        self._emit(
            {
                "type": "episode_start",
                "task_id": plan.task_id,
                "instruction": instruction,
                "scene": scene,
                **self._observer_state(),
            }
        )

        trajectory: list[dict[str, Any]] = []
        failure_reasons: list[str] = []
        total_steps = 0
        invalid_actions = 0
        replan_count = 0
        successful_subtasks = 0
        task_success = True

        for subtask in plan.subtasks:
            queue = list(subtask.tool_calls)
            while queue and total_steps < self.max_steps:
                tool_call = queue.pop(0)
                result = self.tool_registry.execute(tool_call)
                total_steps += 1
                failure_type = "" if result.success else result.data.get("failure_type", "unknown_failure")

                if not result.success:
                    invalid_actions += 1
                    failure_info = self.failure_analyzer.analyze(tool_call, result, subtask, self.env.get_metadata())
                    failure_type = failure_info["failure_type"]
                    failure_reasons.append(failure_type)
                    repair_calls = self.replanner.repair_calls(tool_call, failure_info, replan_count)
                    if repair_calls:
                        if len(repair_calls) == 1 and repair_calls[0] == tool_call:
                            queue = repair_calls + queue
                        else:
                            queue = repair_calls + [tool_call] + queue
                        replan_count += 1
                        self._emit(
                            {
                                "type": "replan",
                                "task_id": plan.task_id,
                                "scene": scene,
                                "step_id": total_steps,
                                "subtask_id": subtask.subtask_id,
                                "tool_name": tool_call.tool_name,
                                "failure_type": failure_type,
                                "repair_call_count": len(repair_calls),
                                "replan_count": replan_count,
                                **self._observer_state(),
                            }
                        )
                    if self.memory:
                        self.memory.add_failure_experience(
                            instruction,
                            scene,
                            subtask.to_dict(),
                            tool_call.to_dict(),
                            failure_type,
                            failure_info.get("repair_strategy", "abort"),
                            False,
                        )

                trajectory_step = self._trajectory_step(total_steps, subtask.subtask_id, tool_call, result, failure_type)
                trajectory.append(trajectory_step)
                self._emit(
                    {
                        "type": "step",
                        "task_id": plan.task_id,
                        "scene": scene,
                        **trajectory_step,
                        **self._observer_state(),
                    }
                )
                if replan_count > self.max_replans:
                    break

            detector_result = self.success_detector.check(subtask, self.env)
            self._emit(
                {
                    "type": "subtask_result",
                    "task_id": plan.task_id,
                    "scene": scene,
                    "subtask_id": subtask.subtask_id,
                    "success": detector_result.success,
                    "message": detector_result.message,
                    **self._observer_state(),
                }
            )
            if detector_result.success:
                successful_subtasks += 1
            else:
                task_success = False
                failure_reasons.append(detector_result.message)
                break

            if total_steps >= self.max_steps or replan_count > self.max_replans:
                task_success = False
                break

        subtask_rate = successful_subtasks / len(plan.subtasks) if plan.subtasks else 0.0
        episode_result = EpisodeResult(
            task_id=plan.task_id,
            instruction=instruction,
            scene=scene,
            success=task_success,
            total_steps=total_steps,
            tool_call_count=total_steps,
            invalid_action_count=invalid_actions,
            replan_count=replan_count,
            subtask_success_rate=subtask_rate,
            failure_reasons=failure_reasons,
            trajectory=trajectory,
        )
        self._emit(
            {
                "type": "episode_end",
                "task_id": plan.task_id,
                "instruction": instruction,
                "scene": scene,
                "success": episode_result.success,
                "total_steps": total_steps,
                "tool_call_count": total_steps,
                "invalid_action_count": invalid_actions,
                "replan_count": replan_count,
                "subtask_success_rate": subtask_rate,
                "failure_reasons": failure_reasons,
                **self._observer_state(),
            }
        )
        return episode_result

    def _trajectory_step(self, step_id: int, subtask_id: str, tool_call: ToolCall, result, failure_type: str) -> dict[str, Any]:
        metadata = result.observation.get("metadata", {})
        objects = metadata.get("objects", []) if isinstance(metadata, dict) else []
        return {
            "step_id": step_id,
            "subtask_id": subtask_id,
            "tool_name": tool_call.tool_name,
            "args": tool_call.args,
            "success": result.success,
            "message": result.message,
            "failure_type": failure_type,
            "metadata_summary": {
                "object_count": len(objects),
                "lastActionSuccess": metadata.get("lastActionSuccess") if isinstance(metadata, dict) else None,
            },
        }

    def _emit(self, event: dict[str, Any]) -> None:
        if self.observer:
            self.observer.on_event(event)

    def _observer_state(self) -> dict[str, Any]:
        visible_objects = []
        if hasattr(self.env, "get_visible_objects"):
            for obj in self.env.get_visible_objects():
                visible_objects.append(
                    {
                        "objectId": obj.get("objectId"),
                        "objectType": obj.get("objectType"),
                        "distance": obj.get("distance"),
                        "visible": obj.get("visible"),
                    }
                )
        agent = self.env.get_agent_state() if hasattr(self.env, "get_agent_state") else {}
        return {"agent": agent, "visible_objects": visible_objects}
