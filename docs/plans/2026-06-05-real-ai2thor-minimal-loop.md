# Real AI2-THOR Minimal Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `put the apple in the fridge` runnable against a real AI2-THOR Unity scene with a minimal high-level closed loop.

**Architecture:** Keep planners isolated from `controller.step`. Add environment helpers for `GetReachablePositions` and `TeleportFull`, upgrade navigation tools to scan reachable positions, and make interaction tools perform one navigate-and-retry pass when an object is visible but out of interaction range.

**Tech Stack:** Python 3.11, AI2-THOR 5.0.0, dataclass schemas, unittest fake-env tests, optional real Unity smoke script.

---

### Task 1: Environment Helpers

**Files:**
- Modify: `embodied_agent/envs/ai2thor_env.py`
- Test: `tests/test_ai2thor_minimal_loop.py`

Add `actionReturn` to `ToolResult.data`, expose `get_reachable_positions()`, and add `teleport(position, rotation, horizon)` using `TeleportFull`.

### Task 2: Teleport-Based Search and Navigate

**Files:**
- Modify: `embodied_agent/tools/navigation_tools.py`
- Test: `tests/test_ai2thor_minimal_loop.py`

Upgrade `search_object` to rotate in place, then iterate reachable positions with `TeleportFull` and local rotations. Upgrade `navigate_to_object` to move near the target if the visible object is beyond a configurable interaction distance.

### Task 3: Interaction Retry

**Files:**
- Modify: `embodied_agent/tools/interaction_tools.py`
- Modify: `embodied_agent/runner/episode_runner.py`
- Test: `tests/test_ai2thor_minimal_loop.py`

For `pick_object`, `open_object`, and `put_object`, retry once after `navigate_to_object` when the direct AI2-THOR action fails. Fix action-failed replanning so it retries once instead of duplicating the failed call twice.

### Task 4: Real Smoke Script

**Files:**
- Create: `scripts/run_ai2thor_minimal.py`
- Modify: `README.md`

Add a script that runs `FloorPlan1: put the apple in the fridge`, saves outputs, and prints the trajectory summary. Document that real Unity execution depends on display/runtime support.
