from __future__ import annotations

from embodied_agent.tools.interaction_tools import register_interaction_tools
from embodied_agent.tools.navigation_tools import register_navigation_tools
from embodied_agent.tools.perception_tools import register_perception_tools
from embodied_agent.tools.state_tools import register_state_tools
from embodied_agent.tools.tool_registry import ToolRegistry


def build_default_tool_registry(env) -> ToolRegistry:
    registry = ToolRegistry()
    register_perception_tools(registry, env)
    register_navigation_tools(registry, env)
    register_interaction_tools(registry, env)
    register_state_tools(registry, env)
    return registry
