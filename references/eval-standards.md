# Evaluation standards (build + audit rubric)

_Last reviewed: 2026-08-29._

This is the checklist both for building a new eval suite (`skills/3-evalset`) and
for auditing an existing one. Each item: **rule → why → how to verify → how to
fix**. In `audit` mode, also check context7 / the web for newer guidance and note
drift rather than trusting this doc blindly.

Scoring an existing setup: mark each item `pass` / `partial` / `fail` /
`n/a`, then rank the `fail`/`partial` items by risk × ease.

---

## E1. Single-turn and multi-turn sets are stored separately
- **Why:** they exercise different failure modes (instruction following vs.
  context tracking, memory, recovery) and need different graders and metrics.
- **Verify:** distinct files (`single_response.jsonl`, `conversations.jsonl`);
  conversation cases have a `turns` array with per-turn assertions.
- **Fix:** split; migrate multi-turn cases out of the single file.

## E2. Both component-level and end-to-end coverage
- **Why:** end-to-end pass rate hides *where* failures happen; component evals
  (retriever recall, router accuracy, single tool call) localize regressions.
- **Verify:** cases tagged by scope; at least the retriever/router and the full
  agent are each measured.
- **Fix:** add targeted cases for each major component.

## E3. Tool-call correctness is measured
- **Why:** agents fan out to many tools; "right answer, wrong/expensive path" is
  a real defect. Check: right tool selected, right arguments, right number of
  steps.
- **Verify:** deterministic `tool_called` graders with argument matchers and a
  `max_steps` budget on tool-using cases.
- **Fix:** add tool-call assertions; record expected tool trajectory.

## E4. Task completion / goal achievement is measured
- **Why:** the user cares whether their goal was met, not token similarity to a
  reference string.
- **Verify:** each case has an explicit goal statement and a grader (deterministic
  or judge-with-rubric) that checks the goal, not surface form.
- **Fix:** rewrite reference-match-only cases around goals.

## E5. Trajectory / trace-based evaluation
- **Why:** an agent can reach the right answer after looping, calling a wrong
  tool then recovering, or frustrating the user. Final-answer checks miss this.
- **Verify:** conversation and tool cases assert on the trace: no redundant
  loops, recovery after an injected tool error, step count, no repeated identical
  calls.
- **Fix:** add trajectory assertions using the trace/span log.

## E6. LLM judge is aligned to human labels
- **Why:** an uncalibrated judge measures the judge, not the agent.
- **Verify:** `evals/judge_alignment.md` exists with judge-vs-human agreement on
  a labeled sample (aim ≥ ~0.8 agreement / adequate kappa); rubric prompt tuned
  to close gaps; re-checked when the judge model changes.
- **Fix:** collect ~10–20 human pass/fail labels, compare, tune rubric, record.

## E7. Deterministic graders used wherever possible
- **Why:** cheaper, faster, reproducible, no judge drift.
- **Verify:** cases with checkable structure use `exact` / `regex` /
  `json_schema` / `contains_*` / `tool_called` / `max_steps` / `latency_budget`;
  judge reserved for genuinely subjective criteria.
- **Fix:** downgrade judge cases to deterministic graders where structure allows.

## E8. Every score is traceable to prompt + model + dataset version
- **Why:** you must be able to attribute a regression to a specific change.
- **Verify:** each results file records agent git SHA, prompt version/hash, model
  id + params, eval-set hash, judge model.
- **Fix:** add this metadata block to `run_evals.py` output.

## E9. Evals are a CI/CD quality gate
- **Why:** manual eval runs get skipped; regressions ship.
- **Verify:** `ci/eval.yml` runs on PRs touching agent code; pre-commit hook
  runs a fast subset; a pass-rate threshold (or "no regression vs baseline")
  blocks merge.
- **Fix:** wire the gate; pick thresholds with the user.

## E10. Dataset is representative and refreshed
- **Why:** a stale hand-picked set diverges from real traffic; agents overfit to it.
- **Verify:** cases sourced from real/expected requests and the spec's example
  requests + feared failure modes; a documented cadence to add cases from
  production traces; hard/edge cases present, not just happy path.
- **Fix:** add a refresh ritual; import failure traces as new cases.

## E11. Sample size is adequate for the decision
- **Why:** a 20-case set can't distinguish a 3-point pass-rate move from noise.
- **Verify:** set size justified against the smallest pass-rate change you need
  to detect (rough rule: tens of cases per capability for POC signal; hundreds
  for release gating); per-tag counts not tiny; report shows counts alongside
  rates.
- **Fix:** grow thin capability slices; report confidence intervals or at least n.

## E12. Safety, grounding, and refusal behavior are evaluated
- **Why:** enterprise agents must refuse out-of-scope / unsafe / unauthorized
  requests and must not hallucinate beyond retrieved context.
- **Verify:** cases tagged `safety` for: prompt injection in retrieved data,
  out-of-scope requests, PII handling, unauthorized action requests, and
  groundedness (answer supported by retrieved sources).
- **Fix:** add a safety slice derived from the spec's compliance + out-of-scope
  sections.

## E13. Regression tracking over time
- **Why:** you need the trend, not a point reading.
- **Verify:** results persisted per run; dashboard shows pass-rate trend per tag;
  a baseline is stored and updated deliberately.
- **Fix:** persist results; add the trend panel (`skills/2-observability`).

## E14. Cost and latency of the eval run itself are known and bounded
- **Why:** evals run on every change; an expensive suite gets disabled.
- **Verify:** judge defaults to local Ollama; if hosted, per-run cost is
  documented and the user consented; suite runtime is tracked.
- **Fix:** move judge local; split fast (pre-commit) vs full (CI/nightly) tiers.

## E15. Pass rates are measured across repeated runs, with variance reported
- **Why:** the agent *and* the LLM judge are both non-deterministic. A pass rate
  from a single run per case is a point sample; the delta against the previous
  run is partly noise, and a real regression can hide inside it. As one
  practitioner put it: *"a 97% pass rate was 97% ± something I had never
  measured, and that something was big enough to hide a regression."*
- **Verify:** `--runs` is >= 3 in CI; results record `runs_per_case`, a noise
  band, and per-case `pass_rate`; the report suppresses deltas inside the band
  rather than presenting them as movement.
- **Fix:** raise `--runs`; pin temperature and seed where the provider allows;
  design graders to accept semantic equivalence rather than byte-exact match.

## E16. Consistency is measured, not just capability
- **Why:** pass@k (succeeded at least once) flatters an unreliable agent. For
  mission-critical behavior the relevant metric is **pass^k** — succeeded in
  *every* attempt. An agent that works two times in three is broken, not 67%
  working.
- **Verify:** the report shows pass^k alongside pass@k and counts flaky cases
  (passed sometimes, failed sometimes). The merge gate uses pass^k.
- **Fix:** treat every flaky case as a defect with a root cause, not a rounding
  error. Flakiness usually indicates an underspecified prompt, an ambiguous
  tool description, or a grader that is itself non-deterministic.

---

## Sources
- Confident AI — *LLM Agent Evaluation Metrics in 2026: Tool Calling, Task
  Completion, Reasoning, and Trace-Based Evals.*
- morphllm — *AI Agent Evaluation (2026): Metrics, Frameworks, and Production
  Failures.*
- MLflow — *Top 5 Agent Evaluation Frameworks in 2026.*
- Future AGI — *LLM Evaluation: Frameworks, Metrics, and Best Practices (2026).*
- arXiv 2505.02820 — *AutoLibra: Agent Metric Induction from Open-Ended Human
  Feedback.*
- arXiv 2507.11277 — *Taming Uncertainty via Automation: Observing, Analyzing,
  and Optimizing Agentic AI Systems.*
- arXiv 2507.21504 — *Evaluation and Benchmarking of LLM Agents: A Survey*
  (pass@k vs pass^k, consistency under repeated runs).
- τ-bench — pass^k as the consistency metric for mission-critical deployments.
