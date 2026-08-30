"""Portable JSON span exporter.

Writes one span per line to ``$TRACE_LOG_DIR/YYYY-MM-DD.jsonl`` in the schema
documented in references/observability-standards.md. This is the vendor-neutral
migration path and is always on. If OTEL_EXPORTER_OTLP_ENDPOINT is set, spans are
also forwarded to OpenTelemetry (best-effort).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def _trace_dir() -> Path:
    """Return the trace log directory from $TRACE_LOG_DIR, creating it if needed."""
    d = Path(os.getenv("TRACE_LOG_DIR", "logs/traces"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_wire(rec: dict[str, Any]) -> dict[str, Any]:
    """Convert an in-memory span record to the portable JSON schema.

    Splits captured content out of `attributes` into a separate `content` block so
    redaction and retention can be reasoned about independently of metadata.
    """

    def iso(ts: float | None) -> str | None:
        """Format an epoch timestamp as RFC3339, or None."""
        return None if ts is None else _dt.datetime.fromtimestamp(ts, _dt.UTC).isoformat()

    attrs = dict(rec.get("attributes") or {})
    content = {"input": attrs.pop("_input", None), "output": rec.get("output")}
    return {
        "trace_id": rec["trace_id"],
        "span_id": rec["span_id"],
        "parent_span_id": rec.get("parent_span_id"),
        "name": rec["name"],
        "start_time": iso(rec.get("start_time")),
        "end_time": iso(rec.get("end_time")),
        "status": rec.get("status", "ok"),
        "error_type": rec.get("error_type"),
        "attributes": {k: v for k, v in attrs.items() if v is not None},
        "content": content,
    }


def write_span(rec: dict[str, Any]) -> None:
    """Append one span record to today's JSONL trace file (thread-safe)."""
    wire = _to_wire(rec)
    path = _trace_dir() / f"{_dt.date.today().isoformat()}.jsonl"
    line = json.dumps(wire, default=str)
    with _lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    _forward_otlp(wire)


def _forward_otlp(wire: dict[str, Any]) -> None:
    """Best-effort forward to an OTLP endpoint; never raises."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:  # pragma: no cover - network path
        import httpx

        httpx.post(f"{endpoint}/v1/traces", json={"_agent_pkg_span": wire}, timeout=1.0)
    except Exception:  # noqa: BLE001
        pass
