"""Unit tests for eval variance handling.

Regression coverage for a methodological bug: the suite originally ran each case
once and reported the delta against the previous run as if it were signal. With a
non-deterministic agent AND a non-deterministic judge, much of that delta was
sampling noise, and a real regression could hide inside it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.run_evals import _consistency, _noise_band, _record, _summarize  # noqa: E402

CASE = {"id": "c1", "tags": {"capability": "x"}, "tier": 1}


def _checks(passed: bool) -> list[dict]:
    return [{"grader": "exact", "passed": passed, "detail": ""}]


def test_record_aggregates_repeated_runs() -> None:
    rec = _record(CASE, "single", [_checks(True), _checks(False), _checks(True)])
    assert rec["runs"] == 3
    assert rec["pass_rate"] == pytest_approx(2 / 3)
    assert rec["pass_any"] is True
    assert rec["pass_all"] is False


def test_gate_is_strict_pass_hat_k() -> None:
    # An agent that works 2 times in 3 is broken, not 67% working.
    flaky = _record(CASE, "single", [_checks(True), _checks(False), _checks(True)])
    solid = _record(CASE, "single", [_checks(True), _checks(True), _checks(True)])
    assert flaky["passed"] is False
    assert solid["passed"] is True


def test_summary_uses_pass_rate_not_single_sample() -> None:
    recs = [
        _record({**CASE, "id": "a"}, "single", [_checks(True), _checks(False)]),
        _record({**CASE, "id": "b"}, "single", [_checks(True), _checks(True)]),
    ]
    # (0.5 + 1.0) / 2
    assert _summarize(recs)["overall"] == 0.75


def test_noise_band_is_zero_when_fully_consistent() -> None:
    recs = [_record(CASE, "single", [_checks(True)] * 3)]
    assert _noise_band(recs) == 0.0


def test_noise_band_grows_with_flakiness() -> None:
    steady = [_record(CASE, "single", [_checks(True)] * 4)]
    flaky = [_record(CASE, "single", [_checks(True), _checks(False)] * 2)]
    assert _noise_band(flaky) > _noise_band(steady)


def test_noise_band_shrinks_with_more_runs() -> None:
    few = [_record(CASE, "single", [_checks(True), _checks(False)])]
    many = [_record(CASE, "single", [_checks(True), _checks(False)] * 8)]
    assert _noise_band(many) < _noise_band(few)


def test_noise_band_shrinks_with_more_cases() -> None:
    one = [_record(CASE, "single", [_checks(True), _checks(False)])]
    ten = [
        _record({**CASE, "id": f"c{i}"}, "single", [_checks(True), _checks(False)])
        for i in range(10)
    ]
    assert _noise_band(ten) < _noise_band(one)


def test_consistency_counts_flaky_cases() -> None:
    recs = [
        _record({**CASE, "id": "a"}, "single", [_checks(True), _checks(True)]),
        _record({**CASE, "id": "b"}, "single", [_checks(True), _checks(False)]),
        _record({**CASE, "id": "c"}, "single", [_checks(False), _checks(False)]),
    ]
    out = _consistency(recs)
    assert out["pass_hat_k"] == pytest_approx(1 / 3)
    assert out["pass_at_k"] == pytest_approx(2 / 3)
    assert out["flaky"] == 1


def test_empty_records_do_not_crash() -> None:
    assert _noise_band([]) == 0.0
    assert _summarize([]) == {}


def pytest_approx(value: float, tol: float = 1e-3) -> float:
    """Tiny helper so these tests read without importing pytest.approx."""

    class _Approx(float):
        def __eq__(self, other: object) -> bool:
            return abs(float(other) - value) < tol  # type: ignore[arg-type]

    return _Approx(value)
