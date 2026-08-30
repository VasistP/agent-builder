# Override registry

Every default this framework enforces, its tier, and what breaks if you change
it. `skills/override` is the only thing allowed to change any of these. Other
skills read this file to know what to refuse.

If a user requests something not listed here, treat it as **Tier B** and add a
row as part of the override.

---

## Tier A — Protected (the non-negotiables)

| Item | Default | Enforced at | Blast radius if overridden |
|------|---------|-------------|----------------------------|
| `evals.enabled` | on | `skills/3-evalset`, `make eval` | No measurement of model behavior at all. Every model-dependent regression ships silently, because deterministic tests deliberately don't cover that path. |
| `evals.ci_gate` | on | `ci/eval.yml` | Evals exist but stop blocking. In practice they rot within weeks — nobody runs a suite that can't fail the build. |
| `evals.judge_alignment` | required | `evals/judge_alignment.md` | Scores measure the judge, not the agent. Pass-rate movements become uninterpretable. |
| `observability.enabled` | on | `skills/2-observability` | No traces. Debugging becomes print statements and guesswork; tool-selection and looping failures are effectively invisible. |
| `observability.json_export` | always on | `src/*/observability/exporter.py` | Vendor lock-in. This export is the migration path; removing it is the one thing that is genuinely hard to undo later. |
| `checkpoints.human_approval` | required between phases | root `SKILL.md` | Phases chain without review. The framework's main safety property is a human reading each phase's output before the next builds on it. |

## Tier B — Structural

| Item | Default | Enforced at | Blast radius |
|------|---------|-------------|--------------|
| `pipeline.phase_order` | 0→6 | root `SKILL.md` | Later phases assume earlier outputs. Reordering usually means evals or observability get built against a moving target. |
| `pipeline.skip_phase` | none skippable | root `SKILL.md` | Depends which. Skipping 4 (tests) is cheap-ish; skipping 0 (discovery) means evals have no ground truth to derive from. |
| `testing.no_fake_model_calls` | enforced | `references/deterministic-testing.md`, `tests/conftest.py` | This is the rule that keeps evals meaningful. Override it and your test suite will appear to cover model behavior while covering nothing. |
| `testing.no_network_guard` | on | `tests/conftest.py` | Deterministic tests can silently start making paid model calls in CI. |
| `docs.docstring_enforcement` | ruff `D`, Google | `pyproject.toml` | `FUNCTIONS.md` and `fn_search` degrade, so every future edit costs more tokens to locate. Compounds slowly. |
| `docs.index_drift_check` | on | `.github/workflows/ci.yml` | The index silently goes stale, which is worse than not having one — agents trust it and edit the wrong function. |
| `repo.layout` | `templates/` structure | `skills/1-scaffold` | Tooling paths (Makefile, CI, index generator) assume it. Changing it is fine if you update those together. |
| `dev.methodology` | TDD (deterministic) + tiered EDD (model) — `references/methodology.md` | `skills/3-evalset`, `skills/4-testing`, `skills/6-feature` | Changes the order of test/eval/implement within a feature and the Tier 1/Tier 2 eval split. |
| `evals.tier_split` | ~30% Tier 1 before code, rest harvested | `skills/3-evalset` | Pushing toward 100% Tier 1 spends the user's scarcest resource on imagined failure modes and anchors the suite; pushing toward 0% means nothing gates the first build. |

## Tier C — Configuration

| Item | Default | Notes |
|------|---------|-------|
| `stack.framework` | Python 3.12 + LangGraph | Genuinely free choice; often mandated by the company. Low risk. |
| `evals.judge_provider` / `judge_model` | `ollama` / `llama3.1:8b` | Switching to hosted costs money per run — always quantify it. |
| `evals.case_counts` | 20–50 single, 5–15 conversations | Below ~20 the pass rate is too noisy to gate on (see `eval-standards.md` E11). |
| `evals.pass_threshold` | no-regression vs baseline | Loosening this is the quiet way to disable the gate; treat a threshold drop >10pts as Tier B. |
| `observability.tool` | by agent type | Free choice among OSS options. JSON export stays on regardless (Tier A). |
| `observability.capture_content` | `false` | Turning on captures prompts/responses — compliance implications; check `spec.md` for PII/regulatory constraints first. |
| `observability.retention` | unbounded | Fine to set; unbounded is the riskier default for volume. |
| `data.stores` | per discovery | Free choice. |
| `mcp.servers` | context7, playwright, memory, sequential-thinking | All optional; removing them only affects dev ergonomics. |
| `dashboard.panels` | O8 must-haves | Removing a must-have panel is Tier B, adding panels is Tier C. |
| `budgets.latency` / `budgets.cost` | per spec | Free choice; they're your own targets. |

---

## Assessment heuristics

Use these to turn repo signals into a verdict. They are starting points — read
the actual repo, and say when it contradicts the heuristic.

### `observability.enabled` → off

| Signal | Verdict |
|--------|---------|
| ≥3 tools, or multi-agent, or any retrieval | **STRONG DISADVANTAGE** — tool-selection and loop failures are the dominant failure class here and are near-impossible to debug without traces |
| Conversational agent with memory/state | **STRONG DISADVANTAGE** — multi-turn bugs need the trajectory |
| Single-shot, 0–1 tools, no retrieval, offline | **NEUTRAL** — but the JSON export alone is ~40 lines and near-zero cost; recommend keeping the export and dropping only the dashboard |
| Traces exist and have been read (results reference them) | **STRONG DISADVANTAGE** — it's already load-bearing |

### `evals.enabled` → off / `evals.ci_gate` → off

| Signal | Verdict |
|--------|---------|
| Eval suite has ever caught a regression (check `evals/results/` history) | **STRONG DISADVANTAGE** — you have direct evidence it works |
| Agent touches enterprise data, makes decisions, or has side-effecting actions | **STRONG DISADVANTAGE** |
| POC with a throwaway horizon, no users, explicitly time-boxed | **DISADVANTAGE but defensible** — offer time-boxed instead of permanent |
| Eval suite is empty or all-passing-trivially | **NEUTRAL on the gate, DISADVANTAGE on evals** — the real problem is the suite is weak; fixing it beats disabling it |
| Judge cost is the actual motivation | **Offer the narrower alternative**: keep the gate, move the judge to local Ollama, or split fast/full tiers |

### `evals.judge_provider` → hosted

Compute and state: cases × avg judge tokens × rate × runs/month. Then:

| Signal | Verdict |
|--------|---------|
| Local judge alignment is poor (<0.8 agreement) and a small hosted model fixes it | **ADVANTAGE** — judge quality is upstream of everything |
| Suite is large and CI runs on every PR | **DISADVANTAGE** — quantify monthly cost; suggest hosted for nightly full runs, local for PR runs |
| Air-gapped / data-residency constraint in `spec.md` | **STRONG DISADVANTAGE** — sending eval content to a hosted API may breach the constraint; flag it as compliance, not cost |

### `testing.no_fake_model_calls` → off

Effectively always **STRONG DISADVANTAGE**. The stated motivation is usually "I
want faster feedback on agent logic" — the narrower alternative is to split the
function so the deterministic pre/post-processing is testable, which gets them
the fast feedback without the false coverage. Offer that first.

### `docs.docstring_enforcement` → off

| Signal | Verdict |
|--------|---------|
| Repo >30 functions, or agents/subagents do the editing | **DISADVANTAGE** — this is the mechanism that keeps future edits cheap; the cost is paid slowly and is hard to attribute later |
| Small repo, single human author, short horizon | **NEUTRAL** |

### `dev.methodology` → strict corpus-first (all evals before any code)

| Signal | Verdict |
|--------|---------|
| Team has repeatedly shipped agents with no evals | **ADVANTAGE** — the discipline benefit may outweigh the anchoring cost for this team specifically |
| Agent domain is well understood, failure modes genuinely predictable (e.g. strict schema extraction) | **NEUTRAL** — Tier 2 harvesting matters less when behavior is narrow |
| Open-ended conversational or multi-tool agent | **DISADVANTAGE** — you cannot predict this failure surface; you'll author 40 cases and discover the real bugs are elsewhere |
| User is time-constrained for interactive authoring | **STRONG DISADVANTAGE** — corpus-first front-loads the most expensive resource in the framework |

### `stack.framework` → change

| Signal | Verdict |
|--------|---------|
| Company mandates a different framework | **ADVANTAGE** — no debate; adapt the skeleton |
| Agent has ≤3 nodes, no checkpointing, no branching | **ADVANTAGE** — LangGraph is overhead at that size; raw SDK is simpler |
| Existing graph is non-trivial and already built | **DISADVANTAGE** — migration cost with no behavioral gain |

### Stacked overrides

If `.agentbuilder/overrides.md` already has active Tier A or B rows, say so
explicitly and describe the *combined* gap, not just the marginal one. Three
individually-defensible overrides routinely add up to an agent with no
regression detection at all, and nobody notices because each was approved
separately.
