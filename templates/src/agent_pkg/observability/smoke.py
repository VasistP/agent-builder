"""Emit a fake traced agent run to verify the observability pipeline.

Run: `python -m agent_pkg.observability.smoke` (or `make smoke`). Produces a root
"agent run" span with one child LLM span and one child tool span, written to the
JSON trace log and forwarded to any configured backend. No model is called.
"""

from __future__ import annotations

from agent_pkg.observability.tracing import span


def main() -> int:
    """Write a synthetic three-span trace and print where it landed."""
    with span(
        "agent run",
        operation="invoke_agent",
        attributes={"gen_ai.conversation.id": "smoke-1"},
    ):
        with span(
            "chat",
            operation="chat",
            attributes={
                "gen_ai.request.model": "smoke-model",
                "gen_ai.usage.input_tokens": 12,
                "gen_ai.usage.output_tokens": 8,
                "cost.usd": 0.0,
            },
        ):
            pass
        with span("execute_tool", operation="execute_tool", attributes={"tool.name": "echo"}) as s:
            s["output"] = "ok"
    print("Smoke trace written to logs/traces/. Open the dashboard (make obs-up).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
