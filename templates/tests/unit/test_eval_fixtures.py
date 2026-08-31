"""Unit tests for the setup/inject fixture mechanism.

An eval case's `setup` is prose — "seed the table with a poisoned row". Nothing
executes prose. Before fixtures existed, such a case ran against a clean data
source and passed, so the indirect-injection and tool-result-injection classes
reported coverage while staging no attack at all. These tests pin the property
that makes that impossible: an unstageable case is a hard error, never a pass.
"""

import pytest

from evals.fixtures import (
    MissingFixtureError,
    applied,
    fixture,
    is_registered,
    turn_key,
)


def test_unregistered_setup_raises_rather_than_skipping() -> None:
    """The whole point: a case that cannot be staged must not silently pass."""
    case = {"id": "adv-999-unregistered", "setup": "seed a poisoned row"}
    with pytest.raises(MissingFixtureError) as exc, applied(case):
        pass
    assert "adv-999-unregistered" in str(exc.value)


def test_registered_setup_runs() -> None:
    calls: list[str] = []

    @fixture("case-setup-only")
    def _setup() -> None:
        calls.append("setup")

    with applied({"id": "case-setup-only", "setup": "x"}):
        calls.append("body")
    assert calls == ["setup", "body"]


def test_generator_fixture_tears_down_even_when_the_case_fails() -> None:
    """A poisoned row left behind would contaminate every later case."""
    calls: list[str] = []

    @fixture("case-with-teardown")
    def _fx():  # type: ignore[no-untyped-def]
        calls.append("setup")
        yield
        calls.append("teardown")

    with pytest.raises(RuntimeError), applied({"id": "case-with-teardown", "setup": "x"}):
        calls.append("body")
        raise RuntimeError("case failed")
    assert calls == ["setup", "body", "teardown"]


def test_is_registered_reports_membership() -> None:
    @fixture("case-membership")
    def _fx() -> None:
        return None

    assert is_registered("case-membership")
    assert not is_registered("case-never-registered")


class TestTurnInjection:
    """Turn-level `inject` must actually fire mid-conversation.

    The first version of this mechanism validated that a fixture existed for a
    conversation case, then flattened every turn to its user string and handed
    the whole list to `chat()`. Validation passed and the fixture was never
    called — an eval asserting recovery from a mid-conversation tool failure ran
    against a perfectly healthy tool.
    """

    def test_turn_key_is_case_scoped(self) -> None:
        assert turn_key("advc-003", 1) == "advc-003#1"
        assert turn_key("advc-003", 1) != turn_key("advc-004", 1)

    def test_inject_fixture_is_looked_up_by_turn_key(self) -> None:
        @fixture("advc-003#1")
        def _fx() -> None:
            return None

        assert is_registered(turn_key("advc-003", 1))
        assert not is_registered(turn_key("advc-003", 0))

    def test_unregistered_turn_inject_raises(self) -> None:
        case = {"id": "advc-404", "turns": [{"user": "hi"}, {"user": "go", "inject": "fail"}]}
        with pytest.raises(MissingFixtureError) as exc:
            with applied(case, what="inject", key=turn_key("advc-404", 1)):
                pass
        assert "advc-404#1" in str(exc.value)

    def test_before_turn_hook_fires_for_every_turn_in_order(self) -> None:
        """The hook chat() exposes is the only place a turn fixture can run."""
        from agent_pkg.agent.run import chat

        seen: list[int] = []
        with pytest.raises(Exception):  # noqa: B017 - no model configured; order is the assertion
            chat(["a", "b"], before_turn=seen.append)
        assert seen == [0], "the hook must run before the turn, not after it"
