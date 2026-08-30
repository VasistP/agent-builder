# agent-builder

An interactive, checkpoint-gated **skill** for standing up a production-grade
enterprise AI-agent POC — with **evaluation and observability wired in before any
agent logic is written**, and a research-grounded rubric for both.

## What it is

`SKILL.md` is the orchestrator. It runs in one of three modes:

- **full** — greenfield: phases 0→6, a mandatory human checkpoint between each.
- **targeted** — "just set up evals" / "just observability" on an existing agent
  codebase, without re-scaffolding or touching agent logic.
- **audit** — score an existing eval / observability setup against the standards
  docs and return a prioritized gap list.

## Layout

| Path | Purpose |
|------|---------|
| `SKILL.md` | orchestrator: modes, non-negotiables, checkpoint protocol |
| `skills/0-discovery` … `skills/7-security` | the phase sub-skills, each independently invocable (`build` / `add` / `audit`) |
| `skills/override` | the **only** way to change any default — assesses the specific repo, warns, offers alternatives, records a ledger |
| `references/override-registry.md` | every overridable item, its tier, blast radius, and assessment heuristics |
| `references/methodology.md` | TDD for deterministic code + tiered EDD for model behavior; the per-feature ordering |
| `references/context-and-cost.md` | the context files (AGENTS.md, ARCHITECTURE/CHANGELOG/TODO) and model-tier routing that stop agents burning tokens re-deriving context |
| `references/security-standards.md` | OWASP Agentic Top 10 rubric: injection, tool scoping, lethal trifecta, blast radius |
| `references/tool-design.md` | tool catalogue design, runtime compaction, MAST multi-agent failure modes |
| `references/eval-standards.md` | research-grounded eval rubric (build + audit) |
| `references/observability-standards.md` | research-grounded observability rubric + portable JSON trace schema |
| `references/eval-authoring-guide.md` | how to co-author cases with the user; JSONL schemas; grader catalogue |
| `references/deterministic-testing.md` | what deterministic tests may/may not cover (no faked model calls) |
| `references/stack-options.md`, `references/observability-options.md`, `references/mcp-catalogue.md` | decision guides |
| `templates/` | the project skeleton `skills/1-scaffold` copies into the target repo |

## Non-negotiables

1. Evals and observability are always set up. Every default — including routine
   config — is locked, and `skills/override` is the only key. Invoking it is
   deliberate friction: a moment to decide whether you actually want the change.
2. Deterministic tests never fabricate model calls — model behavior is measured
   by evals only.
   Deterministic code is built strict-TDD; model behavior uses tiered EDD
   (~30% spec-derived cases up front, the rest harvested from real traces).
3. Observability always writes portable OTel-GenAI-shaped JSON traces
   (`logs/traces/*.jsonl`) — no vendor lock-in.
4. Human checkpoint between every phase.
5. Eval judge defaults to a local Ollama model; hosted judges need explicit
   permission and a cost warning.
6. Every repo gets vendor-neutral `AGENTS.md` + a current-state
   `docs/ARCHITECTURE.md` + append-only `CHANGELOG`/`TODO`, all under enforced
   line budgets, plus model-tier routing — so agents stop re-deriving context
   from source every session.

## The template in `templates/`

Python 3.12 + LangGraph skeleton with: OTel-GenAI instrumentation + JSON export +
a from-scratch Streamlit dashboard, an eval runner (`single_response.jsonl` /
`conversations.jsonl`, mixed deterministic + LLM-judge graders, local Ollama
judge), deterministic unit/regression/integration suites with a no-model-call
guard, a Google-docstring lint gate, a `FUNCTIONS.md` generator + `fn_search.py`
for low-token targeted edits, `.mcp.json` (context7, playwright, memory,
sequential-thinking), and CI (`ci.yml` deterministic, `ci/eval.yml` eval gate).
