# agent-pkg

Enterprise AI agent POC scaffolded by **agent-builder**. Evals and observability
are wired in and non-negotiable.

## Quickstart

```bash
make setup
make test          # deterministic suites, zero tokens
make obs-up        # observability stack
make smoke         # emit a traced fake run — check the dashboard
make eval          # run eval suite (local Ollama judge by default)
```

## Making a change (agents: do this in order)

1. `uv run python tools/fn_search.py "<what you want to change>"` — or read
   `FUNCTIONS.md` — to find the function(s). Do this **before** reading source.
2. Edit; keep the Google-style docstring accurate.
3. `make functions-index` — refresh `FUNCTIONS.md` (CI fails on drift).
4. Add/extend deterministic tests for any non-LLM logic (`docs: deterministic-testing`).
5. `make eval` — report the pass-rate delta. Don't ship a regression.

## Layout

| Path | What |
|------|------|
| `src/agent_pkg/agent/` | graph, state, model shim, entrypoint |
| `src/agent_pkg/tools/` | tool registry + tools |
| `src/agent_pkg/data/` | storage adapters |
| `src/agent_pkg/observability/` | OTel GenAI spans + portable JSON export |
| `evals/` | `single_response.jsonl`, `conversations.jsonl`, judge, graders, runner |
| `tests/{unit,regression,integration}/` | deterministic, token-free |
| `dashboard/` | from-scratch observability dashboard (if selected) |
| `.agentbuilder/` | `spec.md`, `progress.md` |

## Non-negotiables

- Deterministic tests never fake model calls — model behavior is measured by evals.
- Observability always writes `logs/traces/*.jsonl` (portable, vendor-neutral).
- Evals run on every change (pre-commit + CI).
