---
name: agent-builder
description: >-
  Interactive, checkpoint-gated framework for standing up a production-grade
  enterprise AI-agent POC. Use when someone wants to start a new agent project,
  or wants to add/audit evaluations or observability on an existing agentic
  codebase. Walks the user through discovery, scaffolding, observability, eval
  test-set creation, deterministic testing, an agent skeleton, and an
  eval-gated feature loop. Evals and observability are non-negotiable.
---

# agent-builder

A meta-skill that builds the *environment* for an enterprise AI agent before any
agent logic is written, then drives feature work through an eval-gated loop with a
**mandatory human checkpoint between every phase**.

## Non-negotiables

1. **Evaluation** and **observability** are always set up. They cannot be skipped
   from inside this skill or any phase skill.
2. **No fabricated model calls.** Deterministic tests cover only non-LLM
   functions. Anywhere a real model call is required, that path is covered by
   evals — faking it would invalidate the evals.
3. **No vendor lock-in.** Observability always also writes portable
   OpenTelemetry-GenAI-shaped JSON trace logs so the user can migrate tools.
4. **Human checkpoint between phases.** After each phase, print a summary and
   wait for the user to reply `approved` before continuing.
   **Methodology:** strict TDD for deterministic code, tiered EDD for model
   behavior — see `references/methodology.md`. Both kinds of test are written
   before the implementation they cover.
5. **Context files are mandatory.** Every scaffolded repo gets `AGENTS.md`
   (vendor-neutral, with thin `CLAUDE.md`/`GEMINI.md`/Cursor/Copilot pointers),
   `docs/ARCHITECTURE.md` (snapshot — overwritten, never appended),
   `docs/CHANGELOG.md` and `docs/TODO.md` (append-only, rotated), plus model-tier
   routing. These exist to stop agents burning the token budget re-deriving
   context every session. See `references/context-and-cost.md`.
6. **Security is not optional for data/tool agents.** Any agent reading
   enterprise data while holding tool access gets `skills/7-security`: untrusted
   content boundaries, least-privilege tools, approval gates on side effects, and
   injection eval cases. OWASP ranks prompt injection #1, found in over 73% of
   audited systems. See `references/security-standards.md`.
7. **Evals measure reliability, not one sample.** Every case runs 3+ times;
   deltas inside the reported noise band are not treated as signal, and the merge
   gate uses pass^k (every run passed), not pass@k.
8. **API keys need explicit permission.** The eval judge defaults to a local
   Ollama model. Only use a hosted model after asking; if the user picks a large
   paid model, warn that every eval run costs money.

## Everything is locked — `skills/override` is the only key

No skill in this framework may change any default, structure, or configuration
listed in `references/override-registry.md`. That includes routine-looking
config (judge model, latency budgets, MCP list), not just the non-negotiables.

When a user asks any skill to skip, disable, replace, or reconfigure something:

> That's a locked default. I can't change it from here — run
> `skills/override` and I'll assess what it would cost *in this repo*, show you
> the alternatives, and record the decision.

Then stop and let them decide whether to invoke it. Do not pre-assess, do not
pre-argue, and do not treat the request itself as consent. The friction is
deliberate: it gives the user a moment to decide if they actually want it.

Active overrides live in `.agentbuilder/overrides.md`. Read it at the start of
every run — it tells you which guarantees are currently switched off.

## Modes — ask the user first

| Mode | When | What runs |
|------|------|-----------|
| **full** | greenfield project | phases 0 → 6 in order |
| **targeted** | "just set up evals", "just observability", "just security" | jump straight to `skills/2-observability`, `skills/3-evalset`, `skills/4-testing` and/or `skills/7-security` against the existing repo — never re-scaffold, never touch agent logic |
| **audit** | "review our existing eval / observability / security setup" | run the relevant sub-skill(s) in `audit` entry path: score the current setup against `references/eval-standards.md`, `references/observability-standards.md` and `references/security-standards.md`, output a prioritized gap list with rough effort |
| **override** | "skip evals", "change the judge model", "we don't want checkpoints" | hand off to `skills/override` — the only skill permitted to change a default |

Detect a resumable run from `.agentbuilder/progress.md`. If it exists, offer to
resume from the last unapproved phase.

## Phase pipeline (full mode)

| # | Sub-skill | Output | Checkpoint |
|---|-----------|--------|-----------|
| 0 | `skills/0-discovery` | `.agentbuilder/spec.md` | user confirms the spec |
| 1 | `skills/1-scaffold` | project skeleton, tooling, `.mcp.json`, `FUNCTIONS.md` | `make setup && make test` green |
| 2 | `skills/2-observability` | instrumentation + dashboard + JSON trace export | user sees a trace from a smoke call |
| 3 | `skills/3-evalset` | `evals/single_response.jsonl`, `evals/conversations.jsonl`, judge config | `make eval` runs (may be N/A until agent exists) |
| 4 | `skills/4-testing` | deterministic unit/regression/integration suites | suites green, zero tokens used |
| 5 | `skills/5-agent-skeleton` | minimal agent loop + regenerated `FUNCTIONS.md` | one real end-to-end call traced; baseline eval recorded |
| 6 | `skills/6-feature` (repeat) | one feature per run | eval delta shown + human approval before merge |
| 7 | `skills/7-security` | untrusted boundaries, tool scoping, approval gates, injection evals | trifecta verdict recorded; a side-effecting tool is demonstrably blocked |

Phase 7 runs after the skeleton and alongside the feature loop. For any agent
reading enterprise data with tool access it is **mandatory**, not optional.

## Checkpoint protocol

At the end of every phase, output exactly:

```
### Checkpoint: phase <n> — <name>
Done: <bullet list>
Verify yourself: <commands the user should run>
Open risks / decisions: <bullets or "none">

Reply `approved` to continue to phase <n+1>, or tell me what to change.
```

Then update `.agentbuilder/progress.md` (append a row: phase, date, status). Do
not invoke the next sub-skill until the user replies `approved`.

## Standards are research-grounded

`references/eval-standards.md`, `references/observability-standards.md` and
`references/security-standards.md` are the rubric for both building and auditing. Each carries a "Last reviewed" date and a
"Sources" list. In `audit` mode, also check context7 / the web for newer guidance
and flag drift rather than trusting the doc blindly.

## How an agent should navigate a project built by this skill

1. Read `AGENTS.md`, then `docs/ARCHITECTURE.md`, then the tails of
   `docs/TODO.md` and `docs/CHANGELOG.md`. Do not re-derive any of this from the
   codebase — that is the expensive habit these files exist to replace.
2. Run `python tools/fn_search.py "<intent>"` (or read `FUNCTIONS.md`) to locate
   the function(s) to change — do this **before** reading source files.
3. Check the tier: `python tools/route_task.py "<intent>"`. Use the cheapest tier
   that can do the job; decompose rather than escalate.
4. Make the change; keep the Google-style docstring accurate.
5. Run `make functions-index` to refresh `FUNCTIONS.md` (CI fails on drift).
6. Add/extend deterministic tests for any non-LLM logic touched.
7. Run `make eval`; report the score delta.
8. Append to `docs/CHANGELOG.md` and `docs/TODO.md`. If the architecture changed,
   run `make arch-snapshot` before rewriting `docs/ARCHITECTURE.md`.

## MCP servers — vetted and pinned, never ad hoc

Wired into `templates/.mcp.json` by `skills/1-scaffold`, **version-pinned** with a
vetting date each:

- **context7** — current library/framework docs (avoid stale API guesses).
- **playwright** — browser automation for web-interacting agents and dashboard E2E.
- **memory** — persistent knowledge-graph memory for the dev agent across sessions.
- **sequential-thinking** — structured multi-step reasoning for complex builds.

**No server enters `.mcp.json` without passing the vetting checklist in
`references/mcp-catalogue.md`; adding an unvetted one is a Tier B override.**
Tool poisoning — hostile instructions in a tool's description, which the model
reads and the human never sees — is the leading attack on enterprise agents, and
66% of scanned servers carry security findings. Never use a bare `npx -y pkg`.
A database MCP is added only after discovery, with a read-only role.

## Compose with existing skills — don't reimplement them

| Skill | Use it in |
|-------|-----------|
| `dataviz` | `skills/2-observability` — before writing any dashboard chart code |
| `security-review` | `skills/7-security` — over the diff, alongside the S1–S11 rubric |
| `code-review` | `skills/6-feature` — at the pre-merge checkpoint |
| `claude-api` | `skills/3-evalset` — authority for model ids and `evals/pricing.json` |
| `mcp-builder` | when an internal system needs a narrow, purpose-built MCP server |
| `skill-creator` | after the POC, to turn team conventions into reusable skills |
