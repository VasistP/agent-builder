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

Order matters — see `references/methodology.md`. Both kinds of test are written
**before** the implementation.

1. **Pick one feature** from `.agentbuilder/spec.md` → Feature backlog. Restate
   its acceptance criteria with the user.
2. **Locate the code** — `python tools/fn_search.py "<intent>"` and/or read
   `FUNCTIONS.md`. Identify the functions to change/add *before* opening source
   files. Use context7 for any library API you're unsure about.
3. **Write Tier 1 eval cases** — invoke `skills/3-evalset` (build path) to add
   single-response and/or conversation cases capturing this feature's success and
   its feared failure modes. Get the ground truth from the user. Tag
   `"tier": 1, "source": "spec"`.
4. **Write the deterministic tests** for the non-LLM logic this feature needs
   (`skills/4-testing` rules). Run `make test` and **confirm they fail** — a test
   that passes before the code exists is testing nothing.
5. **Implement** the minimal change until the deterministic tests pass. Keep
   Google docstrings accurate.
6. **Refresh index** — `make functions-index`.
7. **Eval** — `make eval`. Show the pass-rate delta overall and per tag vs
   `evals/results/baseline.json` (or the previous run). Investigate any
   regression; do not proceed on a regression without user agreement.
8. **Traces** — run the feature end-to-end; link the new traces; confirm spans
   and cost look sane on the dashboard.
9. **Harvest Tier 2 cases** — turn anything that failed, looped, called the wrong
   tool, or just looked wrong in the traces into new eval cases tagged
   `"tier": 2, "source": "trace:<id>"`. Re-run `make eval`.
   **Never close a checkpoint on an unexplained eval failure with no new case
   recorded** — that is the step teams skip, and it's the one that compounds.
10. **Checkpoint** — print:

```
### Checkpoint: feature — <name>
Change: <summary + files>
New eval cases: <n single / n conversation> (Tier 1: <n>, Tier 2: <n>)
Suite tier mix: <% Tier 1 / % Tier 2>   <flag if still >50% Tier 1>
Eval delta: <overall %, notable per-tag moves>
Tests: <added/passing; confirmed failing before implementation>
Traces: <link / path>
Open risks: <bullets or none>

Reply `approved` to merge, or tell me what to change.
```

11. On `approved`: commit (only if the user asked for commits), update
    `.agentbuilder/progress.md`, and update the baseline if the user wants the
    new result to be the reference.

## Guardrails

- **Locked.** Skipping the eval run, the tests, or the checkpoint for "just this
  one feature" goes through `skills/override` (a one-time scoped override is
  exactly what that skill's `scope: one-time` is for). Never grant it inline.
- Evals and deterministic tests run on **every** change (pre-commit hook + CI).
- If a feature needs a new data source, wire its storage adapter + integration
  test + observability `data source` attribute before the feature logic.
- One feature per branch; keep diffs reviewable.
