"""Tool registration and dispatch.

Deterministic parts (registration, argument parsing, dispatch to a pure tool)
are covered by tests/unit/test_registry.py. Tools that call a model or network
must isolate that call and rely on evals for behavioral coverage.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_pkg.agent.guardrails import ApprovalCallback, require_approval
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
    permission: Permission
    side_effect: bool = False
    declared_at: str = "unknown"

    def posture(self) -> str:
        """One-line summary of this tool's security posture, for `make tools`."""
        effect = "side-effecting" if self.side_effect else "read-only"
        return f"{self.permission.value:<10}  {effect:<14} {self.declared_at}"


@dataclass
class ToolRequest:
    """A parsed request to invoke a tool."""

    name: str
    arguments: dict[str, Any]


ToolFunc = Callable[..., str]


#: Name fragments that usually mean a tool mutates something. Used only to warn
#: when such a tool is declared READ — the check is advisory because naming is a
#: weak signal, but a `delete_*` tool marked read-only is worth a second look.
_MUTATING_HINTS = (
    "create",
    "delete",
    "remove",
    "update",
    "write",
    "send",
    "post",
    "put",
    "insert",
    "drop",
    "execute",
    "run",
    "deploy",
    "pay",
    "charge",
    "email",
)


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    *,
    permission: Permission | None = None,
    side_effect: bool | None = None,
) -> Callable[[ToolFunc], ToolFunc]:
    """Decorator registering `func` as a callable tool.

    Args:
        name: Unique tool name the model refers to.
        description: One line describing when to use it.
        parameters: JSON-schema object for the tool's arguments.
        permission: **Required.** Least-privilege permission this tool needs
            (security S2). There is deliberately no default: a tool nobody
            classified is exactly the one that slips through as READ while
            holding write credentials, and that mistake is invisible until it is
            exploited. One keyword per tool buys the guarantee that every tool's
            authority was a decision.
        side_effect: Whether invoking this changes state outside the agent, which
            routes it through the runtime approval gate (security S3). Defaults
            to True for WRITE/EXTERNAL/ADMIN and False for READ; set it
            explicitly for the exception — a read-only call that still costs
            money, burns rate limit, or pages someone.

    Raises:
        TypeError: If `permission` is omitted.

    Run `make tools` to see every registered tool's posture and the file:line
    where it is declared, which is where you change it.
    """

    def wrap(func: Callable[..., str]) -> Callable[..., str]:
        """Register `func` and return it unchanged."""
        if permission is None:
            raise TypeError(
                f"tool {name!r} must declare a permission. Add one to the decorator:\n"
                f"    @tool({name!r}, ..., permission=Permission.READ)\n"
                f"  Options, in ascending blast radius:\n"
                f"    Permission.READ      cannot mutate anything\n"
                f"    Permission.WRITE     mutates internal state\n"
                f"    Permission.EXTERNAL  can communicate outside the system\n"
                f"    Permission.ADMIN     privileged operations\n"
                f"  There is no default on purpose: an unclassified tool would\n"
                f"  otherwise register as read-only. See `make tools`."
            )
        effect = permission is not Permission.READ if side_effect is None else side_effect
        try:
            src = inspect.getsourcefile(func) or "?"
            line = inspect.getsourcelines(func)[1]
            where = f"{Path(src).name}:{line}"
        except (OSError, TypeError):  # pragma: no cover - non-file callables
            where = "unknown"
        _REGISTRY[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters or {"type": "object"},
            func=func,
            permission=permission,
            side_effect=effect,
            declared_at=where,
        )
        return func

    return wrap


def dispatch(
    name: str,
    arguments: dict[str, Any],
    *,
    granted: frozenset[Permission] | set[Permission] | None = None,
    approver: ApprovalCallback | None = None,
) -> str:
    """Invoke a registered tool by name, enforcing permission then approval.

    This is the single chokepoint every tool call passes through, which is why
    both controls live here rather than in the graph node: a new call path added
    later cannot bypass them by accident.

    Order matters. Permission is checked first — an ungranted tool is refused
    outright and its arguments are never shown to a human, so a prompt injection
    cannot use the approval prompt itself as an output channel.

    Args:
        name: Registered tool name.
        arguments: Keyword arguments for the tool.
        granted: Permissions held by this run. When None, only READ tools may
            run — default-deny, so forgetting to pass grants fails closed
            instead of silently allowing writes.
        approver: Consulted for side-effecting tools. When None, every
            side-effecting call is **denied**: an unattended run must not be able
            to take an irreversible action just because nobody was watching.

    Raises:
        KeyError: If no tool is registered under `name`.
        PermissionDenied: If the tool's permission was not granted.
        ApprovalRequired: If the tool is side-effecting and no approver allowed it.
    """
    if name not in _REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    spec = _REGISTRY[name]
    check_permission(name, spec.permission, granted if granted is not None else {Permission.READ})
    if spec.side_effect:
        require_approval(
            name,
            arguments,
            reason=f"{spec.permission.value} tool with effects outside the agent",
            approver=approver,
        )
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
        lowered = spec.name.lower()
        if spec.permission is Permission.READ and any(h in lowered for h in _MUTATING_HINTS):
            warnings.append(
                f"tool {spec.name!r} is declared READ but its name suggests it mutates "
                f"something. If it does, raise it to WRITE/EXTERNAL at {spec.declared_at} — "
                "a READ tool is never approval-gated."
            )
        if spec.permission is not Permission.READ and not spec.side_effect:
            warnings.append(
                f"tool {spec.name!r} is {spec.permission.value} but marked side_effect=False, "
                f"so it bypasses the approval gate. Confirm that is deliberate "
                f"({spec.declared_at})."
            )

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


def posture_report() -> str:
    """Return the security posture of every registered tool, with where to change it.

    A required `permission` is only reasonable if the current answer is easy to
    see and easy to correct, so this prints the declaration site for each tool.
    Surfaced as `make tools`.
    """
    rows = sorted(_REGISTRY.values(), key=lambda s: (s.permission.value, s.name))
    if not rows:
        return "No tools registered."
    width = max(len(s.name) for s in rows)
    lines = [
        f"{'TOOL'.ljust(width)}  PERMISSION  EFFECT         DECLARED AT",
        f"{'-' * width}  ----------  -------------- -----------",
    ]
    for spec in rows:
        lines.append(f"{spec.name.ljust(width)}  {spec.posture()}")
    gated = sum(1 for s in rows if s.side_effect)
    lines.append("")
    lines.append(
        f"{len(rows)} tools, {gated} approval-gated. Change a posture at the file:line "
        "above.\nSide-effecting tools are denied unless an approver allows them."
    )
    if warnings := audit_tools():
        lines.append("")
        lines.extend(f"  ! {w}" for w in warnings)
    return "\n".join(lines)


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
    permission=Permission.READ,
)
def _echo(text: str) -> str:
    """Return `text` unchanged."""
    return text
