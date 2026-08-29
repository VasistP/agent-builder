"""Tool registry and built-in tools. Register new tools with `@tool`."""

from agent_pkg.tools.registry import dispatch, is_tool_request, tool

__all__ = ["tool", "dispatch", "is_tool_request"]
