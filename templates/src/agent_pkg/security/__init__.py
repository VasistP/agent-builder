"""Security boundaries: untrusted content handling and tool permission scoping.

Implements `references/security-standards.md`. The functions here are
deterministic and unit-tested — enforcement must not depend on the model
behaving well, because the threat model is precisely that it does not.
"""

from agent_pkg.security.permissions import (
    Permission,
    PermissionDenied,
    check_permission,
    describe_grants,
)
from agent_pkg.security.untrusted import (
    UNTRUSTED_PREAMBLE,
    Provenance,
    wrap_untrusted,
)

__all__ = [
    "Permission",
    "PermissionDenied",
    "Provenance",
    "UNTRUSTED_PREAMBLE",
    "check_permission",
    "describe_grants",
    "wrap_untrusted",
]
