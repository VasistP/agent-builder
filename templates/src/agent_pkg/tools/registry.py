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

from agent_pkg.security.permissions import Permission, check_permission

_REGISTRY: dict[str, ToolSpec] = {}


@dataclass
class ToolSpec:
    """A registered tool: its name, schema, callable, and security posture.

    Attributes:
        permission: Least-privilege permission this tool needs (security S2).
        side_effect: True if invoking it changes state outside the agent. Such
            tools route through the runtime approval gate (security S3).
    """

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., str]
    permission: Permission = Permission.READ
    side_effect: bool = False


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


def dispatch(
    name: str,
    arguments: dict[str, Any],
    *,
    granted: frozenset[Permission] | set[Permission] | None = None,
) -> str:
    """Invoke a registered tool by name, enforcing permissions first.

    Args:
        name: Registered tool name.
        arguments: Keyword arguments for the tool.
        granted: Permissions held by this run. When None, only READ tools may
            run — default-deny, so forgetting to pass grants fails closed
            instead of silently allowing writes.

    Raises:
        KeyError: If no tool is registered under `name`.
        PermissionDenied: If the tool's permission was not granted.
    """
    if name not in _REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    spec = _REGISTRY[name]
    check_permission(name, spec.permission, granted if granted is not None else {Permission.READ})
    return spec.func(**arguments)


def audit_tools() -> list[str]:
    """Return warnings about the tool catalogue's design quality.

    Agent performance rises with the first few tools, plateaus, then *declines*
    as the catalogue grows — and overlap hurts more than raw count. Reported
    repeatedly in practice: improving tool descriptions and removing redundancy
    moved reliability more than upgrading the base model.

    Checks: catalogue size, missing or thin descriptions, and name-token overlap
    that suggests two tools the model will confuse.
    """
    warnings: list[str] = []
    specs = list(_REGISTRY.values())

    if len(specs) > 15:
        warnings.append(
            f"{len(specs)} tools registered. Past ~15, selection accuracy usually "
            "declines. Consolidate overlapping tools into one with parameters."
        )

    for spec in specs:
        if len(spec.description.strip()) < 20:
            warnings.append(
                f"tool {spec.name!r} has a thin description; the model selects on "
                "this text, so vagueness here costs more than a weaker model would."
            )
        if not spec.parameters.get("properties") and spec.parameters.get("type") == "object":
            warnings.append(f"tool {spec.name!r} declares no parameter schema.")

    seen: dict[frozenset[str], str] = {}
    for spec in specs:
        tokens = frozenset(re.split(r"[_\-]", spec.name.lower())) - {"get", "list", "the", ""}
        for other_tokens, other_name in seen.items():
            if tokens & other_tokens:
                warnings.append(
                    f"tools {other_name!r} and {spec.name!r} share naming tokens — "
                    "check they are not overlapping; similarity confuses selection "
                    "more than count does."
                )
                break
        seen[tokens] = spec.name

    return warnings


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
