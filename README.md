# agent-builder

An interactive, checkpoint-gated **skill** for standing up a rigorously
evaluated enterprise AI-agent POC — with **evaluation and observability wired in before any
agent logic is written**, and a research-grounded rubric for both.

## What it is

`SKILL.md` is the orchestrator. It runs in one of three modes:

- **full** — greenfield: phases 0→8, a mandatory human checkpoint between each.
- **targeted** — "just set up evals" / "just observability" on an existing agent
  codebase, without re-scaffolding or touching agent logic.
- **audit** — score an existing eval / observability setup against the standards
  docs and return a prioritized gap list.

## How it runs: an interview where it counts

Five phases are **locked to interview mode** — discovery (0), eval sets (3),
every feature (6), security (7) and adversarial testing (8). In those, the agent
asks you questions in small batches, pushes back on vague answers, and reads back
a numbered consensus check you must accept *before* it writes a spec, an eval
case or a threat model to disk. Artifacts are records of what was agreed, never
proposals you are asked to skim.

The test for what gets locked: **can the framework supply a defensible starting
point?** For scaffolding (1), observability (2), tests (4) and the first skeleton
(5) it can — so those run in `propose` mode: it states the default, gets an
explicit yes, and builds. Handing you a blank where a sane default exists just
spends the attention you need for the questions that matter.

The failure mode this prevents is the common one: an agent writes a plausible
markdown plan, you skim it, say "looks good", and every nuance it guessed at is
silently locked in — surfacing three phases later as evals encoding the wrong
ground truth.

Unlocking a phase is possible — a headless CI run has nobody to interview — but
only by **running the override skill and completing its protocol**:

```
skills/override → interaction.interview_mode
```

Typing "override" at a phase, or saying "skip the questions", does nothing; the
phase refuses and points at the skill. Scope is per-phase and recorded that way
(`interaction.interview_mode = propose (phase 3)`), and an unlocked phase falls
back to `propose`, not to silence — the checkpoint is never waivable.

Rules, the consensus-check block, and the per-phase table:
[`references/interview-protocol.md`](references/interview-protocol.md).

Every run opens with a **"Good to know"** block: how the session will run, which
defaults are already locked for you, which of them you can change and at what
ceremony, and what is explicitly out of scope.

## Layout

| Path | Purpose |
|------|---------|
| `SKILL.md` | orchestrator: modes, non-negotiables, checkpoint protocol |
| `skills/0-discovery` … `skills/8-adversarial` | the phase sub-skills, each independently invocable (`build` / `add` / `audit`) |
| `skills/capabilities` | what the framework can do and what you can invoke — see [CAPABILITIES.md](CAPABILITIES.md), generated from live repo state |
| `skills/override` | the **only** way to change any default — assesses the specific repo, warns, offers alternatives, records a ledger |
| `references/interview-protocol.md` | which phases interview vs. propose, how to ask, the consensus check, and how a phase gets unlocked |
| `references/override-registry.md` | every overridable item, its tier, blast radius, and assessment heuristics |
| `references/methodology.md` | TDD for deterministic code + tiered EDD for model behavior; the per-feature ordering |
| `references/context-and-cost.md` | the context files (AGENTS.md, ARCHITECTURE/CHANGELOG/TODO) and model-tier routing that stop agents burning tokens re-deriving context |
| `references/security-standards.md` | OWASP Agentic Top 10 rubric: injection, tool scoping, lethal trifecta, blast radius |
| `references/adversarial-standards.md` | 12-class red-team attack taxonomy; what counts as a breach |
| `references/tool-design.md` | tool catalogue design, runtime compaction, MAST multi-agent failure modes |
| `references/eval-standards.md` | research-grounded eval rubric (build + audit) |
| `references/observability-standards.md` | research-grounded observability rubric + portable JSON trace schema |
| `references/eval-authoring-guide.md` | how to co-author cases with the user; JSONL schemas; grader catalogue |
| `references/deterministic-testing.md` | what deterministic tests may/may not cover (no faked model calls) |
| `references/mcp-catalogue.md` | mandatory MCP vetting standard (tool poisoning, pinning) + the curated server set and companion skills |
| `references/stack-options.md`, `references/observability-options.md` | decision guides |
| `templates/` | the project skeleton `skills/1-scaffold` copies into the target repo |

## Installing it in your coding agent

The framework is plain markdown — `SKILL.md` orchestrates, `skills/*/SKILL.md`
are the phases, `references/*.md` are the rubrics. Any agent that can read files
can run it. The only difference between tools is *how you point the agent at
`SKILL.md`*.

Clone it once:

```bash
git clone https://github.com/<you>/agent-builder.git ~/agent-builder
```

### Claude Code

Skills are auto-discovered from a skills directory. Symlink or copy the repo in:

```bash
mkdir -p ~/.claude/skills
ln -s ~/agent-builder ~/.claude/skills/agent-builder      # personal, all projects
# or, per project:
mkdir -p .claude/skills && ln -s ~/agent-builder .claude/skills/agent-builder
```

Then just ask — `"build me an agent"`, `"set up evals for this repo"`,
`"what can agent-builder do?"` — or invoke it directly with `/agent-builder`.
Sub-skills are separately invocable (`agent-builder-3-evalset`,
`agent-builder-override`, `agent-builder-capabilities`).

### Codex CLI

Codex reads `AGENTS.md`. Add a pointer at the top of your project's `AGENTS.md`
(create one if absent):

```markdown
## agent-builder

When asked to build, evaluate, observe, secure or red-team an AI agent, read
`~/agent-builder/SKILL.md` and follow it. It is interview-first: ask questions
in small batches and reach a consensus check before writing any file in phases
0, 3, 6, 7 and 8; propose defaults in the rest. Phase
sub-skills are in `~/agent-builder/skills/<phase>/SKILL.md`, rubrics in
`~/agent-builder/references/`.
```

For all projects, put the same block in `~/.codex/AGENTS.md`. Codex has no skill
loader — it simply reads the files, which is all this framework needs.

### Cursor

```bash
mkdir -p .cursor/rules
cat > .cursor/rules/agent-builder.mdc <<'RULE'
---
description: agent-builder — interview-first framework for building AI agents
alwaysApply: false
---
When building, evaluating, observing, securing or red-teaming an AI agent, read
`~/agent-builder/SKILL.md` and follow it exactly. Phases 0, 3, 6, 7 and 8 are
interview-locked: questions in small batches, consensus check before any file is
written.
RULE
```

Leave `alwaysApply: false` and reference it with `@agent-builder` when you want
it, so it does not sit in context for unrelated work.

### Gemini CLI

Gemini reads `GEMINI.md` from the project root (and `~/.gemini/GEMINI.md`
globally). Add the same pointer block as the Codex instructions above.

### GitHub Copilot (VS Code / JetBrains)

Add the pointer block to `.github/copilot-instructions.md`, or as a scoped
instruction file:

```bash
mkdir -p .github/instructions
# .github/instructions/agent-builder.instructions.md, with front-matter:
#   ---
#   applyTo: "**"
#   ---
```

### Windsurf

```bash
mkdir -p .windsurf/rules
# .windsurf/rules/agent-builder.md — same pointer block, trigger: model_decision
```

### Aider

Pass the orchestrator in read-only so it never gets edited:

```bash
aider --read ~/agent-builder/SKILL.md --read ~/agent-builder/references/interview-protocol.md
```

### Cline / Roo / Continue / opencode / anything else

All of these read a project rules file (`.clinerules`, `.roo/rules/`,
`.continue/rules/`, `AGENTS.md`). Drop in the same pointer block. If your tool
has no rules mechanism at all, paste this into the chat once per session:

> Read `~/agent-builder/SKILL.md` and follow it for this task. Phases 0, 3, 6, 7
> and 8 are interview-locked — small batches of questions and a consensus check
> before you write anything. Propose defaults for the rest. Checkpoint between
> every phase.

### Verifying the install

Ask the agent *"what can agent-builder do?"*. A correct install answers from
[`CAPABILITIES.md`](CAPABILITIES.md) — every phase, entry paths, CLI tools, make
targets — and a correct **run** opens with the "Good to know" block and its first
question, not with a drafted document.


## Scope

Covers **building, evaluating and observing** an agent — including security
hardening and adversarial testing, since injection resistance is an evaluation
problem and blast-radius control an implementation one.

Out of scope by design: regulatory compliance and data governance, per-user
data authorization / ACL-aware retrieval, and production deployment or secrets
management. Real concerns for enterprise agents, but they belong to compliance
and platform owners. The framework names them and moves on rather than
half-implementing them.

## The golden standard for eval suites

"How many test cases is enough?" is a question most developers have no basis to
answer, so asking it in a prompt yields a number pulled from the air. The
framework **states** a floor instead:

| Suite | Required |
|-------|----------|
| single-response | **20** cases |
| conversations | **5**, 3–8 turns each |
| adversarial | **12** — one per attack class, or a written waiver |
| multi-turn adversarial | **3** |

These are **coverage floors, not statistical power.** They answer "has every
capability and attack class been exercised at all?" At n=20 the 95% margin of
error on a pass rate is ±22 points, so the suite is built to catch gross
regressions and name the case that broke — not to justify "we improved 3%".
Release gating needs hundreds to thousands of cases; the framework says so
rather than implying 20 is enough.

Phase 3 writes the Tier 1 share (6 and 2); phases 5–6 harvest the rest from real
traces. **Phase 8 is the hard gate** — `make eval-coverage-golden` runs in zero
tokens and fails the checkpoint if the suite is short, so an agent cannot be
declared red-teamed while its ordinary behavior rests on six cases.

Shipped schema examples and unspecialized corpus rows (`"example": true`, or a
row still holding `<DATA_SOURCE>`) deliberately **do not count** — otherwise the
scaffold would satisfy its own gate. An attack class that cannot apply is waived
with an `na_reason`, not deleted: a waiver records that someone decided.

Lowering it is a Tier B override (`evals.coverage_floor`), and the assessment
says plainly that you never lower a floor to turn a red build green.

## Non-negotiables

1. Evals and observability are always set up. Every default — including routine
   config — is locked, and `skills/override` is the only key. Invoking it is
   deliberate friction: a moment to decide whether you actually want the change.
2. Deterministic tests never fabricate model calls — model behavior is measured
   by evals only.
   Deterministic code is built strict-TDD; model behavior uses tiered EDD
   (~30% spec-derived cases up front, the rest harvested from real traces).
3. Observability always writes portable OTel-GenAI-*shaped* JSON traces
   (`logs/traces/*.jsonl`) — no vendor lock-in. This is a stable, replayable
   record, **not** a conformant OTLP exporter: for a real collector, add the
   OpenTelemetry SDK's batch processor and OTLP exporter alongside it.
   → `references/observability-standards.md`
4. Human checkpoint between every phase.
5. Eval judge defaults to a local Ollama model; hosted judges need explicit
   permission and a cost warning.
6. Every repo gets vendor-neutral `AGENTS.md` + a current-state
   `docs/ARCHITECTURE.md` + append-only `CHANGELOG`/`TODO`, all under enforced
   line budgets, plus model-tier routing — so agents stop re-deriving context
   from source every session.

## The template in `templates/`

**The template is Python + LangGraph + Anthropic by default, and that default
is wired deeper than one config line.** The eval preflight, model shim and
`.env` keys are provider-aware (`AGENT_MODEL_PROVIDER` selects which key is
required, and `ollama`/`local` needs no key at all), but porting to TypeScript
or another framework means rewriting `tools/`, the Makefile and the graders —
budget real work for it, not a paragraph. The *methodology* is portable; the
scaffold is not yet.

Python 3.12 + LangGraph skeleton with: OTel-GenAI instrumentation + JSON export +
a from-scratch Streamlit dashboard, an eval runner (`single_response.jsonl` /
`conversations.jsonl`, mixed deterministic + LLM-judge graders, local Ollama
judge), deterministic unit/regression/integration suites with a no-model-call
guard, a Google-docstring lint gate, a `FUNCTIONS.md` generator + `fn_search.py`
for low-token targeted edits, `.mcp.json` (context7, playwright, memory,
sequential-thinking), and CI (`ci.yml` deterministic, `ci/eval.yml` eval gate).
