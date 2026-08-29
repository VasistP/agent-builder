---
name: agent-builder-4-testing
description: >-
  Phase 4 of agent-builder. Build deterministic, token-free unit / regression /
  integration test suites covering only non-LLM functions. Use to set up or
  extend the deterministic test harness for an agent project.
---

# Phase 4 — Deterministic test harness (non-negotiable, token-free)

Goal: fast tests that run in CI with **no API key and zero token usage**,
covering every deterministic (non-LLM) function.

Read `references/deterministic-testing.md` first — especially the rule on what
must NOT be faked.

## The rule

- Test only functions whose output is a pure function of their input:
  parsers, query/SQL builders, retrieval ranking on fixed inputs, schema
  validation, tool argument construction & result parsing, state reducers,
  prompt template rendering (string in → string out), cost calculators, redaction.
- **Do not** write fake LLM responses or fake user queries to test model-
  dependent behavior. That belongs to evals (`skills/3-evalset`). Faking it
  invalidates the evals.
- A function that calls a model should be split: deterministic pre/post-
  processing (tested here) around a thin model call (covered by evals).

## Suites

| Suite | Scope | Location |
|-------|-------|----------|
| unit | single pure function | `tests/unit/` |
| regression | deterministic transforms vs golden files | `tests/regression/` + `tests/regression/golden/` |
| integration | wiring of deterministic components + real data-store containers (no model calls) | `tests/integration/` |

- `make test` runs all three; `make test-unit` etc. run one.
- Integration uses `docker compose` test services (Postgres / vector store per
  spec). Marked `@pytest.mark.integration`; skipped if Docker absent, enforced in CI.
- Coverage reported for `src/<pkg>/` excluding the model-call shims (which are
  marked `# pragma: no-eval-cover` and listed in an allowlist).

## Steps

1. Walk `FUNCTIONS.md`; classify each function deterministic vs model-dependent.
2. For each deterministic function with no test, write one (or note it as a gap
   for the feature loop if the function doesn't exist yet).
3. Add golden files for transforms; `make test-regression -- --update-golden`
   regenerates them (human reviews the diff).
4. Ensure CI runs with `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` unset and a guard
   test asserts no outbound model HTTP happened (monkeypatch the transport).

## Checkpoint

Checkpoint block. Verify: `unset ANTHROPIC_API_KEY; make test` green, coverage
report shown, no-network guard passes. User replies `approved`.
