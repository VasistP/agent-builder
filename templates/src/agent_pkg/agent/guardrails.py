"""Deterministic runtime guardrails: budgets, circuit breaker, approval gates.

The recurring finding across production agent reports is that reliability comes
from deterministic enforcement — action-level approval gates, rollback triggers,
circuit breakers — and not from better prompts. Everything here is enforced in
code, on the assumption that the model may be wrong or may have been
manipulated.

Distinct from the framework's build-time human checkpoints: those gate *phases of
development*. These gate *actions at execution time*.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class GuardrailTripped(RuntimeError):
    """Raised when a run exceeds a budget or a breaker opens. Halts the run."""


class ApprovalRequired(RuntimeError):
    """Raised when a side-effecting action needs a human decision.

    Carries the pending action so a durable runtime can suspend the run, ask, and
    resume — see `checkpoint.py`. Not an error condition; it is the mechanism.
    """

    def __init__(self, tool_name: str, arguments: dict[str, Any], reason: str) -> None:
        super().__init__(f"approval required for {tool_name}: {reason}")
        self.tool_name = tool_name
        self.arguments = arguments
        self.reason = reason


@dataclass
class Budgets:
    """Per-run limits that bound blast radius (security S9).

    Defaults are deliberately conservative. Raise them for a specific agent in
    the spec rather than removing the check.
    """

    max_steps: int = 8
    max_tool_calls: int = 20
    max_cost_usd: float = 1.0
    max_wall_seconds: float = 120.0
    max_consecutive_tool_failures: int = 3


@dataclass
class RunGuard:
    """Tracks one agent run against its budgets and trips deterministically.

    Usage:
        guard = RunGuard(budgets=Budgets())
        guard.start()
        guard.on_step()
        guard.on_tool_call("sql_query", ok=True, cost_usd=0.002)
    """

    budgets: Budgets = field(default_factory=Budgets)
    steps: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    started_at: float | None = None
    _consecutive_failures: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def start(self) -> None:
        """Mark the beginning of the run for wall-clock budgeting."""
        self.started_at = time.monotonic()

    def elapsed(self) -> float:
        """Seconds since `start`, or 0.0 if the run has not started."""
        return 0.0 if self.started_at is None else time.monotonic() - self.started_at

    def on_step(self) -> None:
        """Count one reasoning step; trip if over the step or time budget."""
        self.steps += 1
        if self.steps > self.budgets.max_steps:
            raise GuardrailTripped(
                f"step budget exceeded ({self.steps} > {self.budgets.max_steps}). "
                "Looping is the usual cause — check the trace."
            )
        self._check_clock()

    def on_tool_call(self, tool_name: str, *, ok: bool, cost_usd: float = 0.0) -> None:
        """Record a tool invocation and its outcome; trip on budget or breaker.

        The circuit breaker is per-tool and counts *consecutive* failures, so a
        flaky dependency halts the run instead of being retried indefinitely,
        while an unrelated successful tool does not reset an unrelated breaker.
        """
        self.tool_calls += 1
        self.cost_usd += cost_usd

        if self.tool_calls > self.budgets.max_tool_calls:
            raise GuardrailTripped(
                f"tool-call budget exceeded ({self.tool_calls} > {self.budgets.max_tool_calls})"
            )
        if self.cost_usd > self.budgets.max_cost_usd:
            raise GuardrailTripped(
                f"cost budget exceeded (${self.cost_usd:.4f} > ${self.budgets.max_cost_usd:.4f})"
            )

        if ok:
            self._consecutive_failures[tool_name] = 0
        else:
            self._consecutive_failures[tool_name] += 1
            if self._consecutive_failures[tool_name] >= self.budgets.max_consecutive_tool_failures:
                raise GuardrailTripped(
                    f"circuit breaker open for {tool_name!r}: "
                    f"{self._consecutive_failures[tool_name]} consecutive failures"
                )
        self._check_clock()

    def add_cost(self, cost_usd: float) -> None:
        """Add model cost to the run and trip if it exceeds the budget."""
        self.cost_usd += cost_usd
        if self.cost_usd > self.budgets.max_cost_usd:
            raise GuardrailTripped(
                f"cost budget exceeded (${self.cost_usd:.4f} > ${self.budgets.max_cost_usd:.4f})"
            )

    def _check_clock(self) -> None:
        if self.elapsed() > self.budgets.max_wall_seconds:
            raise GuardrailTripped(
                f"wall-clock budget exceeded ({self.elapsed():.1f}s > "
                f"{self.budgets.max_wall_seconds}s)"
            )


ApprovalCallback = Callable[[str, dict[str, Any], str], bool]


def require_approval(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    reason: str,
    approver: ApprovalCallback | None = None,
) -> None:
    """Gate a side-effecting action behind a human decision (security S3).

    Args:
        tool_name: Tool about to run.
        arguments: Its arguments, shown to the approver.
        reason: Why approval is needed, e.g. "writes to the CRM".
        approver: Callable returning True to allow. When None the action is
            **denied** by raising `ApprovalRequired` — default-deny, so a missing
            approver in production fails closed rather than silently proceeding.

    Raises:
        ApprovalRequired: If no approver is wired, or the approver declined.
    """
    if approver is None or not approver(tool_name, arguments, reason):
        raise ApprovalRequired(tool_name, arguments, reason)
