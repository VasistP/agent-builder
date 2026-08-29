"""Integration test: spans written by the tracer are readable back as JSONL.

Exercises the observability wiring (tracing -> exporter -> file) without any
model call. Data-store adapters added per the discovery spec get their own
integration tests here, marked the same way.
"""

from __future__ import annotations

import json

import pytest

from agent_pkg.observability.tracing import span

pytestmark = pytest.mark.integration


def test_span_roundtrip(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACE_LOG_DIR", str(tmp_path))
    with span("agent run", operation="invoke_agent",
              attributes={"gen_ai.conversation.id": "it-1"}):
        with span("execute_tool", operation="execute_tool",
                  attributes={"tool.name": "echo"}) as s:
            s["output"] = "ok"

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    names = {r["name"] for r in rows}
    assert {"agent run", "execute_tool"} <= names
    tool_row = next(r for r in rows if r["name"] == "execute_tool")
    assert tool_row["parent_span_id"] is not None
    assert tool_row["attributes"]["tool.name"] == "echo"
