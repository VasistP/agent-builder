"""Tool registration and dispatch.

Deterministic parts (registration, argument parsing, dispatch to a pure tool)
are covered by tests/unit/test_registry.py. Tools that call a model or network
must isolate that call and rely on evals for behavioral coverage.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_REGISTRY: dict[str, ToolSpec] = {}


@dataclass
class ToolSpec:
    """A registered tool: its name, JSON schema, and callable."""

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., str]


@dataclass
class ToolRequest:
    """A parsed request to invoke a tool."""

    name: str
    arguments: dict[str, Any]


ToolFunc = Callable[..., str]


def tool(
    name: str, description: str, parameters: dict[str, Any] | None = None
) -> Callable[[ToolFunc], ToolFunc]:
    """Decorator registering `func` as a callable tool.

    Args:
        name: Unique tool name the model refers to.
        description: One line describing when to use it.
        parameters: JSON-schema object for the tool's arguments.
    """

    def wrap(func: Callable[..., str]) -> Callable[..., str]:
        """Register `func` and return it unchanged."""
        _REGISTRY[name] = ToolSpec(name, description, parameters or {"type": "object"}, func)
        return func

    return wrap


def dispatch(name: str, arguments: dict[str, Any]) -> str:
    """Invoke a registered tool by name and return its string result."""
    if name not in _REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return _REGISTRY[name].func(**arguments)


def specs() -> list[ToolSpec]:
    """Return all registered tool specs (for building the model tool list)."""
    return list(_REGISTRY.values())


_TOOL_HINT = re.compile(r"^\s*/(?P<name>\w+)\s*(?P<rest>.*)$")


def is_tool_request(text: str) -> ToolRequest | None:
    """Detect an explicit `/toolname args` request in user text (deterministic).

    This placeholder lets the skeleton exercise tool dispatch without the model.
    `skills/5-agent-skeleton` replaces it with model-driven tool selection.
    """
    match = _TOOL_HINT.match(text or "")
    if not match or match.group("name") not in _REGISTRY:
        return None
    return ToolRequest(name=match.group("name"), arguments={"text": match.group("rest").strip()})


@tool(
    "echo",
    "Echo the given text back. Placeholder tool for the skeleton.",
    {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
)
def _echo(text: str) -> str:
    """Return `text` unchanged."""
    return text
