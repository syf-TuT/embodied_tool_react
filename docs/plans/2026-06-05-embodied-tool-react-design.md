# Embodied Tool ReAct Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal runnable Python framework for high-level embodied task planning experiments in AI2-THOR with tool calling, success detection, replanning, memory, and metrics.

**Architecture:** The framework separates high-level planning from environment actions. Planners output `ToolCall` objects, `ToolRegistry` executes registered tools, tools wrap `AI2ThorEnv`, and `EpisodeRunner` controls the closed loop with success detection and replanning.

**Tech Stack:** Python 3.10+, dataclasses, standard-library JSON/CSV/argparse/unittest, optional PyYAML, optional AI2-THOR.

---

### Task 1: Core Schemas and Tool Registry

**Files:**
- Create: `embodied_agent/schemas/data_models.py`
- Create: `embodied_agent/tools/tool_registry.py`
- Test: `tests/test_tool_registry.py`

Write tests for successful tool execution, missing tools, bad arguments, non-`ToolResult` returns, and call history. Implement dataclass models and a registry that always returns `ToolResult`.

### Task 2: Environment Wrapper and Tools

**Files:**
- Create: `embodied_agent/envs/ai2thor_env.py`
- Create: `embodied_agent/tools/perception_tools.py`
- Create: `embodied_agent/tools/navigation_tools.py`
- Create: `embodied_agent/tools/interaction_tools.py`
- Create: `embodied_agent/tools/state_tools.py`

Implement an optional AI2-THOR wrapper. When `ai2thor` is missing, construction raises a clear error. Tool factories accept an env and return callables that operate through env helper methods and return `ToolResult`.

### Task 3: Planners, Detector, Analyzer, Replanner

**Files:**
- Create: `embodied_agent/planners/base_planner.py`
- Create: `embodied_agent/planners/rule_based_planner.py`
- Create: `embodied_agent/planners/mock_llm_planner.py`
- Create: `embodied_agent/detectors/success_detector.py`
- Create: `embodied_agent/replanning/failure_analyzer.py`
- Create: `embodied_agent/replanning/replanner.py`
- Test: `tests/test_success_detector.py`
- Test: `tests/test_failure_analyzer.py`

Support the four requested task templates, success-condition parsing, failure categorization, and bounded repair tool generation.

### Task 4: Runner, Memory, Evaluation, CLI

**Files:**
- Create: `embodied_agent/runner/episode_runner.py`
- Create: `embodied_agent/memory/skill_memory.py`
- Create: `embodied_agent/evaluation/metrics.py`
- Create: `embodied_agent/evaluation/logger.py`
- Create: `main.py`
- Create: `scripts/run_experiments.py`
- Create: `configs/default.yaml`
- Create: `configs/tasks_ai2thor.json`

Implement the episode loop, JSON skill memory, aggregate metrics, output files, and command-line entry points.

### Task 5: Documentation and Verification

**Files:**
- Modify: `README.md`
- Create: `requirements.txt`

Document goals, installation, AI2-THOR setup, supported tools/tasks, and extension points. Create a root virtual environment and verify with `python -m unittest discover -s tests -v`.
