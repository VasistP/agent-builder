"""Tests that the security posture of a tool is actually enforced at dispatch.

The primitives (`check_permission`, `require_approval`) were correct and tested
in isolation long before they were reachable: the `@tool` decorator could not set
a permission, so every tool registered as READ and the approval gate had no
callers. Everything passed, and a `delete_customer` tool would have dispatched as
readily as `echo`.

These tests exist to keep the *wiring* honest. They assert the controls fire
through the public path a real tool call takes, not that the helpers work.
"""

import pytest

from agent_pkg.agent.guardrails import ApprovalRequired
from agent_pkg.security.permissions import Permission, PermissionDenied
from agent_pkg.tools.registry import (
    _REGISTRY,
    ToolSpec,
    audit_tools,
    dispatch,
    posture_report,
    tool,
)


@pytest.fixture
def clean_registry():
    """Register test tools without leaking them into other tests."""
    saved = dict(_REGISTRY)
    _REGISTRY.clear()
    yield _REGISTRY
    _REGISTRY.clear()
    _REGISTRY.update(saved)


def test_permission_is_required(clean_registry) -> None:
    """A tool nobody classified must not quietly register as read-only."""
    with pytest.raises(TypeError) as exc:

        @tool("unclassified", "A tool whose author forgot to think about authority.")
        def _t(text: str) -> str:
            return text

    assert "must declare a permission" in str(exc.value)
    assert "Permission.EXTERNAL" in str(exc.value), "the error must list the options"


def test_ungranted_tool_is_denied_through_dispatch(clean_registry) -> None:
    """The permission check must be reachable, not just correct in isolation."""

    @tool("wipe", "Delete every record.", permission=Permission.ADMIN)
    def _wipe(text: str = "") -> str:  # pragma: no cover - must never run
        raise AssertionError("dispatch allowed an ungranted ADMIN tool to execute")

    with pytest.raises(PermissionDenied):
        dispatch("wipe", {}, granted={Permission.READ})


def test_side_effecting_tool_is_denied_without_an_approver(clean_registry) -> None:
    """An unattended run must not take an irreversible action by default."""

    @tool("send_email", "Send an email to a customer.", permission=Permission.EXTERNAL)
    def _send(to: str = "") -> str:  # pragma: no cover - must never run
        raise AssertionError("a side-effecting tool ran with no approver")

    with pytest.raises(ApprovalRequired):
        dispatch("send_email", {"to": "x@example.com"}, granted={Permission.EXTERNAL})


def test_permission_is_checked_before_approval(clean_registry) -> None:
    """An ungranted tool must not reach the approver.

    Otherwise the approval prompt itself becomes an output channel: an injected
    instruction could smuggle data out inside the arguments shown to a human.
    """
    seen: list[str] = []

    @tool("exfiltrate", "Post data to an external endpoint.", permission=Permission.EXTERNAL)
    def _post(body: str = "") -> str:  # pragma: no cover - must never run
        raise AssertionError("ungranted tool executed")

    def spy(name: str, args: dict, reason: str) -> bool:
        seen.append(name)
        return True

    with pytest.raises(PermissionDenied):
        dispatch("exfiltrate", {"body": "secrets"}, granted={Permission.READ}, approver=spy)
    assert seen == [], "the approver saw the arguments of a tool that was not permitted"


def test_approved_side_effecting_tool_runs(clean_registry) -> None:
    """The gate must be passable, or people will route around it."""

    @tool("write_note", "Write a note to the store.", permission=Permission.WRITE)
    def _write(text: str = "") -> str:
        return f"wrote {text}"

    result = dispatch(
        "write_note",
        {"text": "hi"},
        granted={Permission.WRITE},
        approver=lambda *_: True,
    )
    assert result == "wrote hi"


def test_read_tools_are_not_gated(clean_registry) -> None:
    """Gating reads would make the control expensive enough to be disabled."""

    @tool("lookup", "Look up a record by id.", permission=Permission.READ)
    def _lookup(text: str = "") -> str:
        return "found"

    assert dispatch("lookup", {}) == "found"


def test_side_effect_is_derived_from_permission(clean_registry) -> None:
    """WRITE implies effects outside the agent unless the author says otherwise."""

    @tool("mutate", "Change stored state.", permission=Permission.WRITE)
    def _m() -> str:
        return "ok"

    @tool(
        "expensive_read", "A read that costs money.", permission=Permission.READ, side_effect=True
    )
    def _e() -> str:
        return "ok"

    assert _REGISTRY["mutate"].side_effect is True
    assert _REGISTRY["expensive_read"].side_effect is True


def test_audit_flags_a_mutating_name_declared_read(clean_registry) -> None:
    """A misclassified tool is silent otherwise — nothing else would catch it."""

    @tool("delete_account", "Remove a customer account.", permission=Permission.READ)
    def _d() -> str:
        return "ok"

    assert any("delete_account" in w and "READ" in w for w in audit_tools())


def test_posture_report_shows_where_to_change_it(clean_registry) -> None:
    """A required field is only reasonable if the current answer is discoverable."""

    @tool("charge_card", "Charge a customer's card.", permission=Permission.EXTERNAL)
    def _c() -> str:
        return "ok"

    report = posture_report()
    assert "charge_card" in report
    assert "external" in report
    assert "test_tool_posture.py:" in report, "the report must name the declaration site"
    assert "approval-gated" in report


def test_toolspec_still_requires_permission_positionally() -> None:
    """Constructing a spec directly must not sneak past the requirement either."""
    with pytest.raises(TypeError):
        ToolSpec(name="x", description="y", parameters={}, func=lambda: "z")  # type: ignore[call-arg]
