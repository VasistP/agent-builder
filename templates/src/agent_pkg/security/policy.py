"""What one agent run is allowed to do, and who may approve the rest.

Separated from `permissions.py` because that module answers "is this permission
in the grant set?" while this one answers "what is the grant set for this run,
and who is asked about side effects?". The distinction matters: the first is a
pure check, the second is deployment configuration that differs between an
interactive session, a CI eval run, and production.

The default is the safe one: READ only, no approver. A run that was never
configured can read and nothing else, and any side-effecting tool it reaches for
is denied — an unattended agent must not be able to take an irreversible action
merely because nobody was watching.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_pkg.agent.guardrails import ApprovalCallback
from agent_pkg.security.permissions import Permission, describe_grants


def deny_all(tool_name: str, arguments: dict[str, object], reason: str) -> bool:
    """Approver that refuses everything. The correct approver for eval runs.

    Adversarial cases assert that a side-effecting tool did NOT fire. If eval
    runs auto-approved, those cases would either pass for the wrong reason or —
    worse — actually perform the side effect while red-teaming.
    """
    return False


def cli_approver(tool_name: str, arguments: dict[str, object], reason: str) -> bool:
    """Ask on the terminal. For interactive development only.

    Never wire this into an unattended runtime: with no TTY it raises, and a
    runtime that treats the exception as "allow" would invert the control.
    """
    print(f"\nApproval requested: {tool_name}({arguments})\n  reason: {reason}")
    return input("  allow? [y/N] ").strip().lower() in {"y", "yes"}


@dataclass(frozen=True)
class RunPolicy:
    """Permissions granted to one run, plus the approver for side effects.

    Attributes:
        granted: Permissions this run holds. Defaults to READ only.
        approver: Consulted before any side-effecting tool. None denies.
    """

    granted: frozenset[Permission] = field(default_factory=lambda: frozenset({Permission.READ}))
    approver: ApprovalCallback | None = None

    def describe(self) -> str:
        """Human-readable summary, for traces and the phase 7 audit."""
        who = "no approver (side effects denied)" if self.approver is None else "approver wired"
        return f"grants: {describe_grants(self.granted)}; {who}"
