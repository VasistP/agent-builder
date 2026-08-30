"""Least-privilege tool permissions (security S2, S3).

"Excessive agency" is its own OWASP category: an agent holding a broad tool with
broad credentials can do anything those credentials allow, and a successful
injection inherits exactly that power. Narrow the tool, narrow the credential.

Enforcement is deterministic and happens in `dispatch`, not in the prompt. The
threat model assumes the model has been convinced to misbehave, so a
prompt-level rule is worth nothing here.
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """What a tool is allowed to do.

    Ordered by escalating blast radius. `READ` cannot mutate anything; `WRITE`
    mutates internal state; `EXTERNAL` can communicate outside the system and is
    therefore the leg of the lethal trifecta most worth removing.
    """

    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    ADMIN = "admin"


class PermissionDenied(RuntimeError):
    """Raised when a tool call is not covered by the current grant set."""


def check_permission(
    tool_name: str,
    required: Permission,
    granted: frozenset[Permission] | set[Permission],
) -> None:
    """Raise `PermissionDenied` unless `required` is in `granted`.

    Default-deny: a tool whose permission was never granted cannot run, even if
    the model is convinced it should. There is deliberately no wildcard grant.

    Args:
        tool_name: Name of the tool being invoked, for the error message.
        required: Permission the tool declares it needs.
        granted: Permissions this agent run actually holds.

    Raises:
        PermissionDenied: If the permission is not granted.
    """
    if required not in granted:
        raise PermissionDenied(
            f"tool {tool_name!r} requires {required.value!r} permission, which this "
            f"agent was not granted (has: {sorted(p.value for p in granted) or 'none'})"
        )


def describe_grants(granted: frozenset[Permission] | set[Permission]) -> str:
    """Return a human-readable summary of a grant set, for traces and audits."""
    if not granted:
        return "no permissions"
    return ", ".join(sorted(p.value for p in granted))


def has_lethal_trifecta(
    *, private_data: bool, untrusted_input: bool, granted: frozenset[Permission] | set[Permission]
) -> bool:
    """Return True if this agent combines private data, untrusted input, and egress.

    All three together mean a successful prompt injection can exfiltrate. Any two
    are usually manageable. Assessed at startup and recorded in the spec (S4) so
    the combination is a deliberate, documented decision rather than an accident
    of adding one more tool.
    """
    return private_data and untrusted_input and Permission.EXTERNAL in granted
