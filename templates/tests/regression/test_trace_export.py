"""Regression test: the portable JSON span schema stays stable.

If this fails because the schema genuinely changed, update the golden file with
`pytest tests/regression --update-golden` and review the diff — downstream
importers depend on this shape (observability O7).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_pkg.observability.exporter import _to_wire

GOLDEN = Path(__file__).parent / "golden" / "span_wire.json"


@pytest.fixture
def sample_record() -> dict:
    return {
        "trace_id": "t1",
        "span_id": "s1",
        "parent_span_id": None,
        "name": "chat",
        "start_time": 1_700_000_000.0,
        "end_time": 1_700_000_001.0,
        "status": "ok",
        "error_type": None,
        "attributes": {"gen_ai.request.model": "m", "gen_ai.usage.input_tokens": 3, "_input": None},
        "output": None,
    }


def test_wire_schema(sample_record: dict, request: pytest.FixtureRequest) -> None:
    wire = _to_wire(sample_record)
    if request.config.getoption("--update-golden", default=False):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(wire, indent=2, default=str), encoding="utf-8")
    assert wire == json.loads(GOLDEN.read_text(encoding="utf-8"))
