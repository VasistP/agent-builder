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
| `security.untrusted_boundaries` | on for any agent with external content | `skills/7-security`, `src/*/security/` | Retrieved content is read as instructions. This is OWASP #1 and the most likely way an enterprise-data agent gets used against its owner. |
| `security.tool_permissions` | least privilege, default-deny | `src/*/tools/registry.py` | "Excessive agency": a successful injection inherits whatever the credentials allow. |
| `security.approval_gates` | required for side-effecting tools | `src/*/agent/guardrails.py` | The model deciding to act becomes the same as being allowed to act. Irreversible actions happen with no human in the loop. |
| `evals.multi_run` | >= 3 runs per case | `evals/run_evals.py` | The pass rate becomes a point sample and the gate reports noise as signal — a real regression can hide inside it. |
| `adversarial.breach_gate` | any breach fails the build | `evals/run_evals.py`, `ci/eval.yml` | An attack that works once in three runs is a vulnerability, not flakiness — an attacker retries. Downgrading this to advisory means known-exploitable agents ship. |
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
| `context.files_required` | AGENTS.md + ARCHITECTURE.md + CHANGELOG.md + TODO.md | `skills/1-scaffold` | Agents fall back to re-deriving context from source every session — the single largest avoidable token cost. |
| `context.arch_snapshot_discipline` | snapshot; commit before rewrite | `tools/arch_snapshot.py` | Either the file becomes an append-only log (expensive to read, defeats its purpose) or versions are lost because no commit preserved them. |
| `context.append_only` | CHANGELOG + TODO never rewritten | `AGENTS.md`, review | Loses the record of *why the plan changed* — the most expensive context to reconstruct and the easiest to lose. |
| `mcp.vetting` | every server vetted + version-pinned | `skills/1-scaffold`, `.mcp.json` | Tool poisoning: hostile instructions in a tool description reach the model with high authority and are never seen by a human. 66% of scanned servers have security findings. Unpinned `npx -y` installs unreviewed code on every launch. |
| `context.budgets` | 150/300/200/250 lines | `tools/context_budget.py`, CI | Context files grow until they become the token cost they exist to prevent. |
| `repo.layout` | `templates/` structure | `skills/1-scaffold` | Tooling paths (Makefile, CI, index generator) assume it. Changing it is fine if you update those together. |
| `interaction.interview_mode` | `interview` in phases 0, 3, 6, 7, 8 (questions in small batches + a consensus check before any artifact is written); `propose` in 1, 2, 4, 5 | root `SKILL.md`, those phase skills, `references/interview-protocol.md` | The locked phase reverts to drafting a document and asking "look right?". Users skim; unstated nuance gets locked in as fact, and the first symptom is evals encoding the wrong ground truth several phases later. Cheap to revert, expensive to notice. **Scope is per-phase** — record which phase, never a blanket flag. Only a completed `skills/override` run lifts it; the word "override" typed at a phase skill does not. |
| `dev.methodology` | TDD (deterministic) + tiered EDD (model) — `references/methodology.md` | `skills/3-evalset`, `skills/4-testing`, `skills/6-feature` | Changes the order of test/eval/implement within a feature and the Tier 1/Tier 2 eval split. |
| `evals.tier_split` | ~30% Tier 1 before code, rest harvested | `skills/3-evalset` | Pushing toward 100% Tier 1 spends the user's scarcest resource on imagined failure modes and anchors the suite; pushing toward 0% means nothing gates the first build. |

## Tier C — Configuration

| Item | Default | Notes |
|------|---------|-------|
| `stack.framework` | Python 3.12 + LangGraph | Genuinely free choice; often mandated by the company. Low risk. |
| `evals.judge_provider` / `judge_model` | `ollama` / `llama3.1:8b` | Switching to hosted costs money per run — always quantify it. |
| `evals.case_counts` | 20–50 single, 5–15 conversations | Below ~20 the pass rate is too noisy to gate on (see `eval-standards.md` E11). |
| `evals.runs_per_case` | 3 | Raising it tightens the noise band; dropping below 3 is Tier A, not C — see `evals.multi_run`. |
| `guardrails.budgets` | steps/cost/time/breaker per `Budgets` | Raise per the spec rather than disabling. Removing them entirely is Tier B: they bound blast radius. |
| `tools.catalogue_size` | audited at ~15 | Advisory warning, not a hard block. Overlap matters more than count. |
| `evals.pass_threshold` | no-regression vs baseline | Loosening this is the quiet way to disable the gate; treat a threshold drop >10pts as Tier B. |
| `observability.tool` | by agent type | Free choice among OSS options. JSON export stays on regardless (Tier A). |
| `observability.capture_content` | `false` | Turning on captures prompts/responses — compliance implications; check `spec.md` for PII/regulatory constraints first. |
| `observability.retention` | unbounded | Fine to set; unbounded is the riskier default for volume. |
| `data.stores` | per discovery | Free choice. |
| `mcp.servers` | context7, playwright, memory, sequential-thinking | *Removing* one is Tier C — only dev ergonomics suffer. *Adding* one is gated by `mcp.vetting` (Tier B): each addition widens the supply chain. |
| `models.tier_policy` | nano / standard / deep per `.agent/model-policy.yml` | Editing tier *rules* is Tier C. Removing routing entirely is Tier B — it is the control that stops expensive models doing mechanical work. |
| `models.floors` | ARCHITECTURE.md=deep, evals=standard | Lowering a floor is Tier B: floors exist precisely because keyword matching under-rates these edits. |
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

### `interaction.interview_mode` → `propose` (unlocking phase 0, 3, 6, 7 or 8)

Assess **per phase**, not as one decision. Ask which phase and why before
anything else.

| Signal | Verdict |
|--------|---------|
| Non-interactive run (CI, batch scaffold, headless agent) — nobody is there to answer | **ADVANTAGE** — an interview with no human is a stall; propose mode plus an explicit review step is correct. Applies to all five |
| Phase 0, greenfield, enterprise data in scope | **STRONG DISADVANTAGE** — this is the case the interview exists for; phase 3's ground truth comes from nowhere else |
| Phase 3, and the user wants cases generated from an approved `spec.md` | **DISADVANTAGE** — a generated case tests what the spec *says*, not what the user *meant*. Narrower alternative: generate a draft set, then interview only the pass bars |
| Phase 6, small well-specified feature already in the backlog with acceptance criteria written | **NEUTRAL** — the interview's input already exists; restating it for confirmation is enough |
| Phase 7 or 8, agent with data + tools | **STRONG DISADVANTAGE** — the trifecta verdict and the breach definition are judgement calls about *this* deployment; guessing them makes the security phases theatre |
| Repeat user with a prior `spec.md` for a near-identical agent | **NEUTRAL for phase 0** — offer interviewing only the deltas |
| Stated motivation is speed or impatience | **DISADVANTAGE** — the interview is ~10 minutes; a wrong spec costs days from phase 3 onward. Offer fewer, sharper questions first |

Narrower alternatives, in order of preference: interview only the deltas from an
existing artifact → interview only the judgement calls and propose the rest →
unlock one phase → unlock all five. Record the scope as
`interaction.interview_mode = propose (phase N)`.

Phases 1, 2, 4 and 5 are already `propose`; there is nothing to override there.

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

### `context.*` → weaken or remove

| Signal | Verdict |
|--------|---------|
| Team reports high token spend / hitting budget limits | **STRONG DISADVANTAGE** — these files are the direct mitigation for that exact problem |
| Repo worked on by agents across many sessions | **STRONG DISADVANTAGE** — every cold start re-derives context without them |
| Single-session throwaway prototype, one author | **NEUTRAL** — the payback period may exceed the project's life |
| Motivation is "maintaining them is a chore" | **Offer the narrower alternative**: keep ARCHITECTURE.md + CHANGELOG, drop TODO; or lower the budgets so there is less to maintain. Do not drop AGENTS.md — it is what makes the rest discoverable |

### `models.tier_policy` → remove

| Signal | Verdict |
|--------|---------|
| Team uses one model for everything and is cost-constrained | **STRONG DISADVANTAGE** — routing is the cheapest available saving |
| Team is on a flat-rate plan with no metering | **NEUTRAL** — the saving is latency, not money |
| Policy is producing wrong tiers and annoying people | **Fix the rules, don't remove routing** — tier match patterns are Tier C and easy to tune |

### `security.*` → weaken or remove

Effectively always **STRONG DISADVANTAGE** for an agent with data access and
tools. Before discussing anything else, state the lethal-trifecta verdict.

| Signal | Verdict |
|--------|---------|
| Agent has private data + untrusted input + an external channel | **STRONG DISADVANTAGE** — a successful injection can exfiltrate; this is the case the controls exist for |
| Agent has tools with write or external permission | **STRONG DISADVANTAGE** — excessive agency is its own OWASP category |
| Read-only agent, no external channel, curated internal data only | **DISADVANTAGE but discussable** — the untrusted-content boundary still costs almost nothing to keep |
| Motivation is "approval gates are annoying in dev" | **Offer the narrower alternative**: keep the gate, wire an auto-approver in the dev environment only, and require the real approver in staging and production |

### `mcp.vetting` → skip, or add an unvetted server

| Signal | Verdict |
|--------|---------|
| Server is unpinned (`npx -y pkg` with no version) | **STRONG DISADVANTAGE** — this is the SmartLoader shape; latest is fetched and executed unreviewed on every launch |
| Server would hold database write or admin credentials | **STRONG DISADVANTAGE** — the largest excess-agency risk available; use a read-only role |
| Server is from an unnamed maintainer or unmaintained | **STRONG DISADVANTAGE** — registry presence proves nothing; the trojanized Oura server was in a legitimate registry |
| Official vendor server, pinned, read-only scope, descriptions reviewed | **NEUTRAL** — that *is* passing the gate; just record the vetting date |
| Motivation is "vetting is slow" | **Offer the narrower alternative**: vet once, pin, and re-vet only on version bump — that is a few minutes per server per quarter |

### `adversarial.*` → weaken, skip, or make advisory

| Signal | Verdict |
|--------|---------|
| Agent has tools with write or external permission | **STRONG DISADVANTAGE** — these are the classes with real blast radius |
| Agent reads content authored outside your company | **STRONG DISADVANTAGE** — indirect injection (A2) is the most likely break and needs continuous coverage |
| Corpus is still generic placeholders | **The gate is already worthless** — fix specialization before debating whether to keep it |
| Read-only agent, curated internal data, no external channel | **DISADVANTAGE but discussable** — scope escape and secret extraction still apply cheaply |
| Motivation is suite runtime | **Offer the narrower alternative**: fast subset on PR, full suite nightly — that is already the default |

### `evals.multi_run` → 1 run per case

| Signal | Verdict |
|--------|---------|
| Used as a merge gate | **STRONG DISADVANTAGE** — a single run cannot distinguish a regression from sampling noise, so the gate becomes theater |
| Used as a fast local smoke check, full suite still runs in CI | **NEUTRAL** — this is the intended split; `--runs 1` already prints a warning |
| Motivation is eval runtime or cost | **Offer the narrower alternative**: fast tier with 1 run on pre-commit, full multi-run suite in CI or nightly |

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
