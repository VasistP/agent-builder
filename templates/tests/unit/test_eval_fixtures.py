"""Unit tests for the setup/inject fixture mechanism.

An eval case's `setup` is prose — "seed the table with a poisoned row". Nothing
executes prose. Before fixtures existed, such a case ran against a clean data
source and passed, so the indirect-injection and tool-result-injection classes
reported coverage while staging no attack at all. These tests pin the property
that makes that impossible: an unstageable case is a hard error, never a pass.
"""

import pytest

from evals.fixtures import MissingFixtureError, applied, fixture, is_registered


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
