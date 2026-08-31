"""Portable JSON span exporter.

Writes one span per line to ``$TRACE_LOG_DIR/YYYY-MM-DD.jsonl`` in the schema
documented in references/observability-standards.md. This is the vendor-neutral
migration path and is always on.

If ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, spans are ALSO exported through the
real OpenTelemetry SDK — ``BatchSpanProcessor`` + ``OTLPSpanExporter``.

This previously posted a hand-built JSON body to ``{endpoint}/v1/traces`` and
swallowed every exception. That was not OTLP on any axis (wrong envelope, wrong
field casing, RFC3339 instead of unix-nanos, map instead of AnyValue attributes,
no resource or scope), so a collector answered 400 and the spans vanished with no
error shown — configured-looking and completely inert, which is worse than not
offering the feature. It was also synchronous on the request path.

The SDK path fixes all of that: correct wire format, batched off-thread export,
and real failure reporting. The JSONL export stays regardless; it is the
portability guarantee, and it does not depend on a collector existing.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()

#: The GenAI semantic conventions are still marked Development upstream, so the
#: version emitted is pinned and stated rather than tracking whatever the
#: installed SDK happens to default to. Expect attribute renames across bumps.
GENAI_SCHEMA_URL = "https://opentelemetry.io/schemas/1.27.0"


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
    _export_otlp(rec, wire)


_otel_lock = threading.Lock()

#: The GenAI semantic conventions are still marked Development upstream, so the
#: version emitted is pinned and stated rather than tracking whatever the
#: installed SDK happens to default to. Expect attribute renames across bumps.
GENAI_SCHEMA_URL = "https://opentelemetry.io/schemas/1.27.0"
_otel_tracer: Any | None = None
_otel_unavailable: str | None = None


def _tracer() -> Any | None:
    """Return a configured OTel tracer, or None when OTLP export is off.

    Built once, lazily. A failure to construct it is reported once and then
    remembered, rather than retried per span or silently ignored.
    """
    global _otel_tracer, _otel_unavailable
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    if _otel_tracer is not None or _otel_unavailable is not None:
        return _otel_tracer
    with _otel_lock:
        if _otel_tracer is not None or _otel_unavailable is not None:
            return _otel_tracer
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            resource = Resource.create(
                {
                    "service.name": os.getenv("OTEL_SERVICE_NAME", "agent-pkg"),
                    "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
                }
            )
            provider = TracerProvider(resource=resource)
            # Batched and off-thread: export must not sit on the request path.
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            _otel_tracer = provider.get_tracer(
                "agent_pkg",
                schema_url=GENAI_SCHEMA_URL,
            )
        except ImportError as exc:
            _otel_unavailable = (
                f"OTEL_EXPORTER_OTLP_ENDPOINT is set but the OTLP exporter is not "
                f"installed ({exc}). Install it:\n"
                f"    uv add opentelemetry-exporter-otlp-proto-http\n"
                f"  JSONL export continues regardless."
            )
            print(f"WARNING: {_otel_unavailable}")
        except Exception as exc:  # noqa: BLE001 - never break the agent over telemetry
            _otel_unavailable = f"OTLP export could not start: {type(exc).__name__}: {exc}"
            print(f"WARNING: {_otel_unavailable}")
    return _otel_tracer


def _export_otlp(rec: dict[str, Any], wire: dict[str, Any]) -> None:
    """Emit one span through the OpenTelemetry SDK, if OTLP export is configured."""
    tracer = _tracer()
    if tracer is None:
        return
    from opentelemetry.trace import Status, StatusCode

    start_ns = int((rec.get("start_time") or 0) * 1e9)
    end_ns = int((rec.get("end_time") or 0) * 1e9)
    # OTLP attribute values must be primitives; anything else is dropped rather
    # than stringified, so a structured value is visible in the JSONL export only.
    attributes = {
        k: v for k, v in wire["attributes"].items() if isinstance(v, str | int | float | bool)
    }
    otel_span = tracer.start_span(rec["name"], start_time=start_ns, attributes=attributes)
    if wire.get("status") != "ok":
        otel_span.set_status(Status(StatusCode.ERROR, wire.get("error_type") or ""))
    otel_span.end(end_time=end_ns or None)
