"""Unit tests for deterministic graders."""

from evals.graders import run_grader


def test_contains_all() -> None:
    r = run_grader({"type": "contains_all", "values": ["cat", "dog"]}, "cat and DOG")
    assert r["passed"]


def test_tool_called_counts() -> None:
    r = run_grader(
        {"type": "tool_called", "name": "sql", "times": 2}, "x", tool_calls=["sql", "sql"], steps=2
    )
    assert r["passed"]


def test_max_steps_fail() -> None:
    r = run_grader({"type": "max_steps", "value": 3}, "x", steps=5, tool_calls=[])
    assert not r["passed"]


def test_regex_negate() -> None:
    r = run_grader({"type": "regex", "pattern": r"\d", "negate": True}, "no digits here")
    assert r["passed"]
