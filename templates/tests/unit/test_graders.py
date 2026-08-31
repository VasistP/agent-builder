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


# --- graders the authoring guide documents; these pin that they exist and work.
# Each of these was documented in references/eval-authoring-guide.md while being
# either absent from the registry or implemented as a weaker check than the docs
# claimed, which is the failure mode where a green suite measures nothing.


def test_tool_called_args_match_requires_matching_arguments() -> None:
    """Right tool, wrong arguments is a distinct and common failure."""
    events = [{"name": "sql", "args": {"table": "orders"}, "output": "", "error": None}]
    spec = {"type": "tool_called", "name": "sql", "args_match": {"table": "customers"}}
    result = run_grader(spec, "", tool_calls=["sql"], tool_events=events, steps=1, latency_s=0.0)
    assert not result["passed"]

    events[0]["args"]["table"] = "customers"
    result = run_grader(spec, "", tool_calls=["sql"], tool_events=events, steps=1, latency_s=0.0)
    assert result["passed"]


def test_tool_called_args_match_is_a_subset_check() -> None:
    """Extra arguments the case does not mention must not fail it."""
    events = [{"name": "sql", "args": {"table": "customers", "limit": 10}, "error": None}]
    spec = {"type": "tool_called", "name": "sql", "args_match": {"table": "customers"}}
    assert run_grader(spec, "", tool_calls=["sql"], tool_events=events, steps=1, latency_s=0.0)[
        "passed"
    ]


def test_recovered_from_error_needs_an_actual_error() -> None:
    """With no error in the trajectory the case tested nothing, so it must not pass."""
    events = [{"name": "sql", "args": {}, "output": "ok", "error": None}]
    result = run_grader(
        {"type": "recovered_from_error"},
        "here is your answer",
        tool_calls=["sql"],
        tool_events=events,
        steps=1,
        latency_s=0.0,
    )
    assert not result["passed"]
    assert "nothing to recover from" in result["detail"]


def test_recovered_from_error_passes_on_retry_after_failure() -> None:
    """An error followed by a successful call and a real answer is recovery."""
    events = [
        {"name": "sql", "args": {}, "output": "", "error": "Timeout"},
        {"name": "sql", "args": {}, "output": "3 rows", "error": None},
    ]
    assert run_grader(
        {"type": "recovered_from_error"},
        "There are 3 matching orders.",
        tool_calls=["sql", "sql"],
        tool_events=events,
        steps=2,
        latency_s=0.0,
    )["passed"]


def test_json_schema_validates_types_not_just_key_presence() -> None:
    """A required-keys check passes output that violates the declared schema."""
    schema = {
        "type": "object",
        "required": ["count"],
        "properties": {"count": {"type": "integer"}},
    }
    spec = {"type": "json_schema", "schema": schema}
    assert not run_grader(spec, '{"count": "seven"}', tool_calls=[], steps=1, latency_s=0.0)[
        "passed"
    ]
    assert run_grader(spec, '{"count": 7}', tool_calls=[], steps=1, latency_s=0.0)["passed"]
