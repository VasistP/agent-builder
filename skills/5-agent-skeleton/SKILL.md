---
name: agent-builder-5-agent-skeleton
description: >-
  Phase 5 of agent-builder. Build the minimal agent loop (LangGraph or chosen
  framework) with typed state, a tool registry, full docstrings, observability
  wired in, and a regenerated FUNCTIONS.md. Use once the environment is ready.
---

# Phase 5 — Agent skeleton

Goal: the smallest possible working agent that exercises the whole environment —
one real end-to-end call, traced, with a baseline eval run recorded. No backlog
features yet.

**Propose, don't interrogate.** This phase has defensible defaults, so state the
single end-to-end path you'll prove and its success criterion up front, get an
explicit yes on the path, if more than one is plausible, then build. No
consensus-check ceremony — but no silent decisions either, and the phase
checkpoint still applies. → `references/interview-protocol.md`

## Prerequisites

Phases 1–4 (skeleton, observability, evals, tests) approved. In `add` mode
against an existing agent, skip this phase.

## Build

1. **State** — typed (`TypedDict` / Pydantic) conversation + scratchpad state.
2. **Graph** — minimal LangGraph: `receive → plan → (tool?) → respond`. One
   example tool (e.g. `echo` or a trivial read against a spec data source).
3. **Model client shim** — single wrapper in `src/<pkg>/agent/model.py`; the
   only place a model is called; instrumented with an `llm call` span; on the
   no-eval-cover allowlist.
4. **Tool registry** — `src/<pkg>/tools/registry.py`: decorator that registers a
   tool with name, JSON schema, and a Google docstring; dispatch emits `tool call`
   spans.
5. **Observability** — confirm root `agent run` span wraps the graph; conversation
   id propagated.
6. **Entrypoint** — `src/<pkg>/agent/run.py:run_once(request) -> Response` and a
   `chat()` loop; this is what `evals/run_evals.py` calls.
7. **Docstrings everywhere**; then `make functions-index`.

## Verify

- `python -m <pkg> "hello"` returns a response; trace visible in dashboard + in
  `logs/traces/`.
- `make eval` runs the real agent against the current sets; record the result as
  `evals/results/baseline.json` and note the pass rate.
- `make test` still green; `FUNCTIONS.md` up to date (CI drift check passes).

## Checkpoint

Checkpoint block. Include the baseline eval pass rate and a link to the first
trace. User replies `approved` before starting the feature loop.
