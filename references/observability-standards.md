# Observability standards (build + audit rubric)

_Last reviewed: 2026-08-29._

Rubric for building (`skills/2-observability`) and auditing agent observability.
Each item: **rule → why → how to verify → how to fix**. In `audit` mode also
check context7 / the web for newer OTel GenAI guidance and note drift.

---

## O1. OpenTelemetry GenAI semantic conventions are the schema
- **Why:** a standard schema keeps telemetry consistent across frameworks and
  lets you switch backends without re-instrumenting. Don't invent a custom format.
- **Verify:** spans use `gen_ai.*` attribute names; operations named per the
  conventions (`chat`, `execute_tool`, `embeddings`, agent invoke…).
- **Fix:** rename attributes; adopt an OTel GenAI instrumentation lib or the
  `templates/src/<pkg>/observability/` wrappers.

## O2. Span hierarchy reflects the reasoning chain
- **Why:** you need to see *where* time/tokens/errors go within one request.
- **Verify:** root `agent run` span per request; child spans for every LLM call,
  tool call, and retrieval step; parent/child links intact; conversation id on all.
- **Fix:** wrap the graph entrypoint; add span decorators to the model shim and
  tool dispatch.

## O3. Token and cost metrics per model and per agent
- **Why:** cost control and regression detection ("this change doubled tokens").
- **Verify:** `gen_ai.usage.input_tokens` / `output_tokens` on every LLM span;
  cost derived via `evals/pricing.json`; dashboard breaks down by model and by
  agent/node.
- **Fix:** populate usage attributes from provider responses; add the pricing map.

## O4. Tool usage and failure patterns are visible
- **Why:** wrong-tool selection, argument errors, and flaky tools are top agent
  failure modes.
- **Verify:** per-tool call count, error rate, latency, and argument/exception
  detail (redacted) on the dashboard.
- **Fix:** add status + error type to tool spans; add the tool panel.

## O5. Eval scores are first-class telemetry
- **Why:** OTel GenAI conventions deliberately do **not** cover output quality or
  safety scoring — the eval layer fills that gap, and the two must join up.
- **Verify:** `make eval` results written back as span attributes and/or a
  metrics table; dashboard shows the pass-rate trend next to latency/cost.
- **Fix:** have `run_evals.py` emit scores to the same store the dashboard reads.

## O6. Content redaction at the instrumentation level
- **Why:** prompts/responses over enterprise data contain PII; logging them by
  default is a compliance breach.
- **Verify:** capture is metadata-only unless `OTEL_GENAI_CAPTURE_CONTENT=true`;
  redaction of known PII patterns even when content capture is on; documented.
- **Fix:** gate body capture behind the env var; add a redaction filter.

## O7. Portable JSON trace export always on
- **Why:** no vendor lock-in — the user must be able to move to another tool.
- **Verify:** every span also written to `logs/traces/YYYY-MM-DD.jsonl` in a
  documented schema; a documented importer path to at least one other tool.
- **Fix:** add the JSON span exporter alongside whatever backend is used.

## O8. Dashboard has the must-have panels
- **Why:** these are the minimum to operate an agent.
- **Verify:** request volume & latency (p50/p95/p99), tokens & cost over time,
  tool-call counts + failure rate, error breakdown by type, eval score trend,
  trace explorer (drill into one request).
- **Fix:** add missing panels.

## O9. Alerting thresholds are defined
- **Why:** silent degradation (latency creep, error-rate spike, cost blowout,
  eval-score drop) should page someone.
- **Verify:** thresholds documented for latency, error rate, per-request cost,
  and eval pass rate; wired to whatever notification path the team uses.
- **Fix:** set thresholds with the user; add alert rules.

## O10. Trace / conversation id correlation across the stack
- **Why:** you need to jump from a user complaint to the exact trace, and from a
  trace to its eval result and logs.
- **Verify:** one id propagated through spans, structured logs, and eval records.
- **Fix:** thread the id from the entrypoint; add it to the log formatter.

## O11. Instrumentation adds negligible overhead and never breaks the agent
- **Why:** observability must not be the reason a request fails.
- **Verify:** exporter runs async / batched; span code is exception-safe
  (failures logged, not raised); load-tested.
- **Fix:** wrap span emission in try/except; use a batch span processor.

## O12. Retention and volume are managed
- **Why:** trace volume grows fast; unbounded storage costs money and slows queries.
- **Verify:** retention policy on `logs/traces/` and the backend; optional
  sampling for high volume (keep all errors + eval-sampled traffic).
- **Fix:** add rotation/retention; add tail-based sampling if needed.

---

## Portable JSON trace schema (`logs/traces/*.jsonl`)

One span per line:

```json
{
  "trace_id": "…", "span_id": "…", "parent_span_id": "…|null",
  "name": "agent run | chat | execute_tool | retrieval",
  "start_time": "RFC3339", "end_time": "RFC3339",
  "status": "ok | error", "error_type": "…|null",
  "attributes": {
    "gen_ai.operation.name": "…",
    "gen_ai.request.model": "…",
    "gen_ai.usage.input_tokens": 0,
    "gen_ai.usage.output_tokens": 0,
    "gen_ai.conversation.id": "…",
    "tool.name": "…", "tool.arguments": "…(redacted)…",
    "data_source": "…",
    "cost.usd": 0.0
  },
  "content": {"input": null, "output": null}
}
```

`content` is populated only when `OTEL_GENAI_CAPTURE_CONTENT=true`.

---

## Sources
- OpenTelemetry blog — *AI Agent Observability: Evolving Standards and Best
  Practices* (2025).
- OpenTelemetry — GenAI semantic conventions (semantic-conventions repo,
  `gen_ai` namespace).
- Datadog — *Agent Observability natively supports OpenTelemetry GenAI Semantic
  Conventions* (2026).
- Greptime — *How OpenTelemetry Traces LLM Calls, Agent Reasoning, and MCP Tools*
  (2026).
- Uptrace — *OpenTelemetry for AI Systems: LLM and Agent Observability* (2026).
- Fiddler AI — *OpenTelemetry for AI Observability: What It Covers and Where It
  Stops.*
- arXiv 2507.11277 — *Taming Uncertainty via Automation: Observing, Analyzing,
  and Optimizing Agentic AI Systems.*
