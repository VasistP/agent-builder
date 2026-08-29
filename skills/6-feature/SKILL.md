---
name: agent-builder-6-feature
description: >-
  Phase 6 of agent-builder, repeatable. Implement exactly ONE feature from the
  backlog, eval-gated, with a mandatory human checkpoint before merge. Use for
  each incremental feature after the agent skeleton exists.
---

# Phase 6 — Feature loop (one feature per run)

Goal: add one backlog feature safely. Never batch features; never merge without
a human checkpoint and an eval run.

## Steps

1. **Pick one feature** from `.agentbuilder/spec.md` → Feature backlog. Restate
   its acceptance criteria with the user.
2. **Locate the code** — `python tools/fn_search.py "<intent>"` and/or read
   `FUNCTIONS.md`. Identify the functions to change/add *before* opening source
   files. Use context7 for any library API you're unsure about.
3. **Add eval cases first** — invoke `skills/3-evalset` (build path) to add
   single-response and/or conversation cases that capture this feature's success
   and its feared failure modes. Get the ground truth from the user.
4. **Implement** the minimal change. Keep Google docstrings accurate.
5. **Deterministic tests** — add/extend `tests/` for any non-LLM logic touched
   (`skills/4-testing` rules). Run `make test`.
6. **Refresh index** — `make functions-index`.
7. **Eval** — `make eval`. Show the pass-rate delta overall and per tag vs
   `evals/results/baseline.json` (or the previous run). Investigate any
   regression; do not proceed on a regression without user agreement.
8. **Traces** — run the feature end-to-end; link the new traces; confirm spans
   and cost look sane on the dashboard.
9. **Checkpoint** — print:

```
### Checkpoint: feature — <name>
Change: <summary + files>
New eval cases: <n single / n conversation>
Eval delta: <overall %, notable per-tag moves>
Tests: <added/passing>
Traces: <link / path>
Open risks: <bullets or none>

Reply `approved` to merge, or tell me what to change.
```

10. On `approved`: commit (only if the user asked for commits), update
    `.agentbuilder/progress.md`, and update the baseline if the user wants the
    new result to be the reference.

## Guardrails

- Evals and deterministic tests run on **every** change (pre-commit hook + CI).
- If a feature needs a new data source, wire its storage adapter + integration
  test + observability `data source` attribute before the feature logic.
- One feature per branch; keep diffs reviewable.
