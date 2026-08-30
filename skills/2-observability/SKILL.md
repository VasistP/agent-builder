---
name: agent-builder-2-observability
description: >-
  Phase 2 of agent-builder. Set up open-source agent observability chosen by
  agent type, always with a portable OpenTelemetry-GenAI JSON trace export, plus
  a dashboard. Has build / add / audit entry paths. Use to set up or review
  observability for an AI agent.
---

# Phase 2 — Observability (non-negotiable)

Goal: every agent run emits structured telemetry following the OpenTelemetry
GenAI semantic conventions, is viewable on a dashboard, and is exportable as
portable JSON so the tool can be swapped later.

**Propose, don't interrogate.** This phase has defensible defaults, so state the
observability tool for this agent type, content capture (default off — turning
it on has PII implications) and retention up front, get an explicit yes on any
of those three the spec doesn't already settle, then build. No consensus-check
ceremony — but no silent decisions either, and the phase checkpoint still
applies. → `references/interview-protocol.md`

Read `references/observability-standards.md` first — it is the rubric.

**Locked** — defaults here can only change via `skills/override`; refuse and point there.

## Entry paths

- **build** — greenfield (full pipeline). Wire instrumentation into the skeleton.
- **add** — existing agent codebase. Instrument it without changing agent logic:
  wrap the model client and tool dispatch, add span decorators. Show a diff and
  get approval before applying.
- **audit** — existing observability setup. Score it against
  `references/observability-standards.md`, check context7 / web for newer
  guidance, output a prioritized gap list (rule, current state, fix, rough
  effort). No code changes unless the user then asks.

## Choosing the tool (OSS only, no paid subscription)

| Agent type | Default | Why |
|-----------|---------|-----|
| tool/workflow, RAG, multi-agent | **Langfuse** (self-host via compose) OR **Arize Phoenix** (OTel-native) | rich trace tree, eval-score attachment, prompt versioning |
| single-shot Q&A, or user has "no idea" | **from-scratch dashboard** | minimal deps: JSON span log + small Streamlit/FastAPI reader |

Always ask the user's preference first; if they have none and the agent is
simple, build from scratch. Never require an account or API key.

## Always do this regardless of tool

1. **Instrument to OTel GenAI conventions.** Spans: `agent run` (root) →
   `llm call` / `tool call` / `retrieval` children. Attributes: `gen_ai.operation.name`,
   `gen_ai.request.model`, `gen_ai.usage.input_tokens` / `output_tokens`,
   `gen_ai.conversation.id`, tool name + args + result status, data source,
   error type. See `templates/src/<pkg>/observability/`.
2. **Portable JSON export.** Every span is also written as newline-delimited JSON
   to `logs/traces/YYYY-MM-DD.jsonl` in a documented schema. This is the
   migration path — `references/observability-standards.md` documents it.
3. **Cost & token metrics** per model and per agent, derived from spans +
   `evals/pricing.json`.
4. **Content redaction** at instrumentation level, controlled by
   `OTEL_GENAI_CAPTURE_CONTENT` env var (default: metadata only, no prompt/response
   bodies). Document how to enable full capture in a safe environment.
5. **Eval scores as telemetry.** `skills/3-evalset` writes eval results back as
   span attributes / a metrics table the dashboard reads.
6. **If the `dataviz` skill is available, use it before writing chart code.**
   If not, fall back per `.agent/integrations.yml`: one palette, every axis
   labelled, readable in light and dark, stat row over dense grid.
7. **Dashboard panels (must-have):** request volume & latency (p50/p95), tokens &
   cost over time, tool-call counts + failure rate, error breakdown, eval score
   trend, trace explorer.

## `make obs-up` / `make obs-down`

Bring the chosen stack up/down via `docker compose`. From-scratch dashboard runs
as a compose service reading `logs/traces/`.

**Bind-mount gotcha — check this before debugging an empty dashboard.** The
dashboard reads traces through a bind mount, so the project must live under a
path the Docker runtime shares into its VM. Colima/Lima mount `$HOME` but **not**
`/tmp`; Docker Desktop has a configurable file-sharing list. A project outside
those paths produces an empty dashboard with **no error message**. Verify with
`docker compose exec dashboard ls /app/logs/traces` before assuming the
instrumentation is broken.

## Verify

Run a smoke script (`python -m <pkg>.observability.smoke`) that emits a fake
agent run with one llm span + one tool span. Confirm it appears in the dashboard
AND in `logs/traces/`.

## Checkpoint

Checkpoint block. Verify: `make obs-up` then the smoke script, then open the
dashboard URL. User replies `approved`.
