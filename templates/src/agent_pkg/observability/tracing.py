"""Span helpers following OpenTelemetry GenAI semantic conventions.

This module is intentionally dependency-light: it emits spans to the portable
JSON exporter always, and (if an OTLP endpoint is configured) to OpenTelemetry.
It must never raise into caller code (observability O11).
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import time
import uuid
from collections.abc import Iterator
from typing import Any

from agent_pkg.observability.exporter import write_span
from agent_pkg.observability.redaction import redact

_current_trace: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)
_current_span: contextvars.ContextVar[str | None] = contextvars.ContextVar("span_id", default=None)
_usage: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "usage", default=None
)


def _capture_content() -> bool:
    """Return True if prompt/response bodies may be persisted (observability O6)."""
    return os.getenv("OTEL_GENAI_CAPTURE_CONTENT", "false").lower() == "true"


@contextlib.contextmanager
def span(
    name: str,
    *,
    operation: str | None = None,
    attributes: dict[str, Any] | None = None,
    input_content: Any = None,
) -> Iterator[dict[str, Any]]:
    """Open a span; yields a mutable dict you can add result attributes to.

    Args:
        name: Span name, e.g. "agent run", "chat", "execute_tool", "retrieval".
        operation: gen_ai.operation.name value (chat, execute_tool, embeddings...).
        attributes: Initial span attributes (gen_ai.* keys preferred).
        input_content: Optional prompt/args; only persisted if content capture is on.

    Yields:
        A dict; set ``attributes`` / ``output`` / ``error_type`` on it before exit.
    """
    trace_id = _current_trace.get() or uuid.uuid4().hex
    parent = _current_span.get()
    span_id = uuid.uuid4().hex[:16]
    t_trace = _current_trace.set(trace_id)
    t_span = _current_span.set(span_id)

    rec: dict[str, Any] = {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent,
        "name": name,
        "start_time": time.time(),
        "status": "ok",
        "error_type": None,
        "attributes": {"gen_ai.operation.name": operation, **(attributes or {})},
        "output": None,
    }
    if _capture_content() and input_content is not None:
        rec["attributes"]["_input"] = redact(input_content)

    try:
        yield rec
    except Exception as exc:  # noqa: BLE001 - record and re-raise
        rec["status"] = "error"
        rec["error_type"] = type(exc).__name__
        raise
    finally:
        rec["end_time"] = time.time()
        if not _capture_content():
            rec["output"] = None
        elif rec["output"] is not None:
            rec["output"] = redact(rec["output"])
        with contextlib.suppress(Exception):
            write_span(rec)
        _current_trace.reset(t_trace)
        _current_span.reset(t_span)


def record_llm_usage(input_tokens: int, output_tokens: int, model: str, cost_usd: float) -> None:
    """Record token usage + cost for the most recent LLM call.

    The model shim reads this back via `pop_usage` when closing its span; see
    agent/model.py.
    """
    _usage.set(
        {
            "input": input_tokens,
            "output": output_tokens,
            "model": model,
            "cost_usd": cost_usd,
        }
    )


def pop_usage() -> dict[str, Any] | None:
    """Return and clear the last recorded LLM usage frame."""
    frame = _usage.get()
    _usage.set(None)
    return frame
