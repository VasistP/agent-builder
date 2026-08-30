"""Unit tests for runtime guardrails, checkpointing, and idempotency.

Deterministic enforcement — these must hold without any model involvement.
"""

import pytest

from agent_pkg.agent.checkpoint import (
    Checkpoint,
    CheckpointStore,
    idempotency_key,
    run_once_idempotent,
)
from agent_pkg.agent.guardrails import (
    ApprovalRequired,
    Budgets,
    GuardrailTripped,
    RunGuard,
    require_approval,
)


class TestBudgets:
    def test_step_budget_trips(self) -> None:
        guard = RunGuard(budgets=Budgets(max_steps=2))
        guard.start()
        guard.on_step()
        guard.on_step()
        with pytest.raises(GuardrailTripped, match="step budget"):
            guard.on_step()

    def test_tool_call_budget_trips(self) -> None:
        guard = RunGuard(budgets=Budgets(max_tool_calls=1))
        guard.start()
        guard.on_tool_call("t", ok=True)
        with pytest.raises(GuardrailTripped, match="tool-call budget"):
            guard.on_tool_call("t", ok=True)

    def test_cost_budget_trips(self) -> None:
        guard = RunGuard(budgets=Budgets(max_cost_usd=0.01))
        guard.start()
        with pytest.raises(GuardrailTripped, match="cost budget"):
            guard.add_cost(0.02)

    def test_wall_clock_budget_trips(self) -> None:
        guard = RunGuard(budgets=Budgets(max_wall_seconds=0.0))
        guard.start()
        with pytest.raises(GuardrailTripped, match="wall-clock"):
            guard.on_step()


class TestCircuitBreaker:
    def test_opens_after_consecutive_failures(self) -> None:
        guard = RunGuard(budgets=Budgets(max_consecutive_tool_failures=3))
        guard.start()
        guard.on_tool_call("flaky", ok=False)
        guard.on_tool_call("flaky", ok=False)
        with pytest.raises(GuardrailTripped, match="circuit breaker"):
            guard.on_tool_call("flaky", ok=False)

    def test_success_resets_the_breaker(self) -> None:
        guard = RunGuard(budgets=Budgets(max_consecutive_tool_failures=2))
        guard.start()
        guard.on_tool_call("t", ok=False)
        guard.on_tool_call("t", ok=True)
        guard.on_tool_call("t", ok=False)  # count restarted, must not trip

    def test_breakers_are_per_tool(self) -> None:
        # An unrelated tool's failures must not open another tool's breaker.
        guard = RunGuard(budgets=Budgets(max_consecutive_tool_failures=2))
        guard.start()
        guard.on_tool_call("a", ok=False)
        guard.on_tool_call("b", ok=False)
        guard.on_tool_call("a", ok=True)


class TestApprovalGate:
    def test_missing_approver_denies(self) -> None:
        # Default-deny: a missing approver in production must fail closed.
        with pytest.raises(ApprovalRequired) as exc:
            require_approval("crm_write", {"id": 1}, reason="writes to the CRM")
        assert exc.value.tool_name == "crm_write"
        assert exc.value.arguments == {"id": 1}

    def test_declining_approver_denies(self) -> None:
        with pytest.raises(ApprovalRequired):
            require_approval("t", {}, reason="r", approver=lambda *_: False)

    def test_approving_allows(self) -> None:
        require_approval("t", {}, reason="r", approver=lambda *_: True)


class TestIdempotency:
    def test_same_call_yields_same_key(self) -> None:
        a = idempotency_key("run1", "send_email", {"to": "x", "body": "y"})
        b = idempotency_key("run1", "send_email", {"body": "y", "to": "x"})
        assert a == b, "argument ordering must not change the key"

    def test_different_runs_yield_different_keys(self) -> None:
        assert idempotency_key("run1", "t", {}) != idempotency_key("run2", "t", {})

    def test_different_arguments_yield_different_keys(self) -> None:
        assert idempotency_key("r", "t", {"a": 1}) != idempotency_key("r", "t", {"a": 2})

    def test_effect_runs_once_across_replays(self) -> None:
        cp = Checkpoint(run_id="r1")
        calls = []

        def effect() -> str:
            calls.append(1)
            return "sent"

        first = run_once_idempotent(cp, "send_email", {"to": "x"}, effect)
        second = run_once_idempotent(cp, "send_email", {"to": "x"}, effect)
        assert first == second == "sent"
        assert len(calls) == 1, "replay must reuse the recorded result, not re-send"


class TestCheckpointStore:
    def test_roundtrip(self, tmp_path) -> None:
        store = CheckpointStore(tmp_path)
        cp = Checkpoint(run_id="r1", step=3, state={"messages": ["hi"]})
        store.save(cp)
        loaded = store.load("r1")
        assert loaded is not None
        assert loaded.step == 3
        assert loaded.state == {"messages": ["hi"]}

    def test_missing_run_returns_none(self, tmp_path) -> None:
        assert CheckpointStore(tmp_path).load("nope") is None

    def test_save_is_atomic_leaving_no_temp_file(self, tmp_path) -> None:
        store = CheckpointStore(tmp_path)
        store.save(Checkpoint(run_id="r1"))
        assert not list(tmp_path.glob("*.tmp"))

    def test_delete_removes_and_is_idempotent(self, tmp_path) -> None:
        store = CheckpointStore(tmp_path)
        store.save(Checkpoint(run_id="r1"))
        store.delete("r1")
        store.delete("r1")  # must not raise
        assert store.load("r1") is None

    def test_run_id_is_sanitized_into_the_path(self, tmp_path) -> None:
        store = CheckpointStore(tmp_path)
        store.save(Checkpoint(run_id="../../etc/passwd"))
        assert not (tmp_path.parent.parent / "etc").exists()
