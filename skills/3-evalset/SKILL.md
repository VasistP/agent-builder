---
name: agent-builder-3-evalset
description: >-
  Phase 3 of agent-builder. Co-author evaluation test sets with the user —
  separate single-response and conversation sets stored as JSONL — with mixed
  deterministic + LLM-judge grading and a local Ollama judge by default. Has
  build / add / audit entry paths. Use to create or review an agent eval suite.
---

# Phase 3 — Evaluation test sets (non-negotiable)

Goal: two version-controlled test sets that run on every code change:
`evals/single_response.jsonl` and `evals/conversations.jsonl`, plus a judge
configuration and `evals/run_evals.py`.

Read `references/eval-standards.md` (the rubric) and
`references/eval-authoring-guide.md` (how to co-write good cases) first.

## Entry paths

- **build** / **add** — create the sets interactively (below). `add` works
  against an existing agent; it just needs a callable entrypoint.
- **audit** — score an existing `evals/` setup against `references/eval-standards.md`
  (single vs multi-turn separated? tool-call correctness? task completion?
  trajectory checks? judge aligned to human labels? scores traceable to
  prompt/model/dataset version? wired as a CI gate? dataset representative &
  refreshed? sample size adequate? safety/grounding covered?). Check context7 /
  web for newer practice. Output prioritized gaps + effort. No changes unless asked.

## Before you start — warn the user

> Creating a good eval set is interactive and takes real time. You must be present
> to provide the *ground-truth* answers and to play the human side of each
> conversation. I will not invent expected answers or user turns — that would make
> the evals meaningless.

Then ask:

1. **How many single-response cases?** (suggest 20–50 for a POC; more for
   higher-stakes agents — cite `references/eval-standards.md` on sample size.)
2. **How many conversations?** (suggest 5–15, each 3–8 turns.)
3. Time budget now vs. split across sessions? (Sets can grow incrementally;
   `run_evals.py` picks up whatever is in the files.)

## Judge setup

- Default: **local Ollama** model (e.g. `llama3.1:8b` or `qwen2.5:7b`), fixed
  seed, temperature 0. Zero cost, offline. `make eval` starts Ollama via compose
  if needed.
- If the user wants a hosted judge: **ask permission explicitly**. Recommend a
  small model (Claude Haiku). If they choose a large paid model, warn in writing:
  *"every `make eval` run will cost money — roughly $X per full run at N cases."*
- Judge config in `evals/judge.py` + `.env` (`EVAL_JUDGE_PROVIDER`,
  `EVAL_JUDGE_MODEL`).
- **Judge alignment:** collect the user's own pass/fail label on ~10 sample
  outputs, compare to the judge, tune the rubric prompt until they agree. Record
  agreement rate in `evals/judge_alignment.md`.

## Authoring loop (per case)

Do this one case at a time, with the user:

1. User gives the input (single request, or the first user turn).
2. Discuss the *ground truth*: what a correct response must contain / must not
   contain / what tools it should call / step budget.
3. Pick grader(s):
   - **deterministic** where possible: `exact`, `regex`, `json_schema`,
     `contains_all` / `contains_none`, `tool_called` (name + arg matchers),
     `max_steps`, `latency_budget`.
   - **llm_judge** with a written rubric for anything subjective (helpfulness,
     tone, grounding, refusal correctness).
   - Cases usually combine both.
4. For conversations: capture each expected user turn and per-turn + end-of-
   conversation assertions (goal achieved? no loops? recovered from tool error?).
5. Append to the correct JSONL file (see schema in `references/eval-authoring-guide.md`).
6. Tag each case: `capability`, `difficulty`, `data_source`, `safety` so reports
   can slice.

## Storage — keep them separate

- `evals/single_response.jsonl` — one JSON object per line, one turn.
- `evals/conversations.jsonl` — one JSON object per line, `turns` array.
- `evals/rubrics/*.md` — reusable judge rubrics referenced by id.
- Never mix the two files.

## `make eval`

Runs `evals/run_evals.py`: loads both sets, invokes the agent entrypoint per
case, runs graders, writes `evals/results/<timestamp>.json` + updates a trend
table the observability dashboard reads. Prints pass rate overall and per tag,
plus a diff vs the previous run.

Wire it as a CI gate (`ci/eval.yml`) and a pre-commit hook: evals run on every
change to agent code.

## Checkpoint

Checkpoint block. Verify: `make eval` runs against the current agent (or a stub
and reports N/A pre-skeleton), files exist and are separate, judge runs locally.
User replies `approved`.
