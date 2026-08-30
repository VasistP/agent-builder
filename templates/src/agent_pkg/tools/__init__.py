"""Tool registry and built-in tools. Register new tools with `@tool`."""

from agent_pkg.tools.registry import audit_tools, dispatch, is_tool_request, specs, tool

__all__ = ["tool", "dispatch", "is_tool_request", "specs", "audit_tools"]
