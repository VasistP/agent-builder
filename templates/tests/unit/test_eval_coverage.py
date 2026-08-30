"""Unit tests for the golden-standard coverage gate.

The gate exists because "how many eval cases is enough?" is a question most
developers have no basis to answer, and the honest answer depends on statistics
they should not have to derive. Leaving it to a prompt produced suites of four
cases that reported a confident pass rate. These tests pin the two properties
that make the gate worth having: unspecialized template rows never count as
coverage, and the adversarial standard binds at the phase 8 stage.

Token-free: counting JSONL rows calls no model.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals import run_evals  # noqa: E402

REAL = {"id": "x", "class": "direct_injection", "input": "hi", "graders": []}


def _write(tmp_path: Path, name: str, cases: list[dict]) -> None:
    (tmp_path / name).write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")


@pytest.fixture
def eval_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the runner at an empty temp eval directory."""
    monkeypatch.setattr(run_evals, "EVAL_DIR", tmp_path)
    for name in run_evals.COVERAGE_FLOOR:
        _write(tmp_path, name, [])
    return tmp_path


def test_shipped_examples_do_not_count(eval_dir: Path) -> None:
    """A schema example must never satisfy the floor it exists to explain."""
    _write(eval_dir, "single_response.jsonl", [{**REAL, "example": True}] * 30)
    _, blocked = run_evals.coverage_report(stage="tier1")
    assert blocked


def test_unspecialized_placeholders_do_not_count(eval_dir: Path) -> None:
    """A corpus row still holding <DATA_SOURCE> was never aimed at this agent."""
    generic = {**REAL, "input": "Summarize the latest record from <DATA_SOURCE>."}
    _write(eval_dir, "adversarial.jsonl", [generic] * 20)
    lines, _ = run_evals.coverage_report(stage="golden")
    assert any("0 / 12" in line for line in lines)


def test_tier1_stage_does_not_demand_an_adversarial_suite(eval_dir: Path) -> None:
    """Phases 3-6 legitimately run before the red-team suite exists."""
    _write(eval_dir, "single_response.jsonl", [REAL] * 6)
    _write(eval_dir, "conversations.jsonl", [REAL] * 2)
    _, blocked = run_evals.coverage_report(stage="tier1")
    assert not blocked


def test_golden_stage_binds_the_adversarial_standard(eval_dir: Path) -> None:
    """Meeting the capability standard is not enough to clear phase 8."""
    _write(eval_dir, "single_response.jsonl", [REAL] * 20)
    _write(eval_dir, "conversations.jsonl", [REAL] * 5)
    _, blocked = run_evals.coverage_report(stage="golden")
    assert blocked


def test_first_real_adversarial_case_promotes_the_stage(eval_dir: Path) -> None:
    """A half-built red-team suite is the state that reads as covered and is not."""
    _write(eval_dir, "single_response.jsonl", [REAL] * 20)
    _write(eval_dir, "conversations.jsonl", [REAL] * 5)
    _, blocked = run_evals.coverage_report()
    assert not blocked
    _write(eval_dir, "adversarial.jsonl", [REAL])
    _, blocked = run_evals.coverage_report()
    assert blocked


def test_a_waived_class_counts_as_decided(eval_dir: Path) -> None:
    """'Does not apply here' is an answer; silence is not."""
    waived = [
        {**REAL, "class": k, "na_reason": "no external channel"} for k in run_evals.ATTACK_CLASSES
    ]
    _write(eval_dir, "adversarial.jsonl", waived)
    assert not run_evals._missing_attack_classes(waived, [])


def test_allow_thin_reports_but_does_not_block(eval_dir: Path) -> None:
    """Local authoring needs an escape hatch; CI does not use it."""
    lines, blocked = run_evals.coverage_report(allow_thin=True, stage="golden")
    assert not blocked
    assert any("--allow-thin" in line for line in lines)
