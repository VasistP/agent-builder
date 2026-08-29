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
   from inside this skill. (A separate `agent-builder-override` skill will exist
   for teams that must opt out; do not implement opt-out here.)
2. **No fabricated model calls.** Deterministic tests cover only non-LLM
   functions. Anywhere a real model call is required, that path is covered by
   evals — faking it would invalidate the evals.
3. **No vendor lock-in.** Observability always also writes portable
   OpenTelemetry-GenAI-shaped JSON trace logs so the user can migrate tools.
4. **Human checkpoint between phases.** After each phase, print a summary and
   wait for the user to reply `approved` before continuing.
5. **API keys need explicit permission.** The eval judge defaults to a local
   Ollama model. Only use a hosted model after asking; if the user picks a large
   paid model, warn that every eval run costs money.

## Modes — ask the user first

| Mode | When | What runs |
|------|------|-----------|
| **full** | greenfield project | phases 0 → 6 in order |
| **targeted** | "just set up evals", "just observability", "evals + observability" | jump straight to `skills/2-observability` and/or `skills/3-evalset` (and `skills/4-testing` if asked) against the existing repo — never re-scaffold, never touch agent logic |
| **audit** | "review our existing eval / observability setup" | run the relevant sub-skill(s) in `audit` entry path: score the current setup against `references/eval-standards.md` / `references/observability-standards.md`, output a prioritized gap list with rough effort |

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

`references/eval-standards.md` and `references/observability-standards.md` are the
rubric for both building and auditing. Each carries a "Last reviewed" date and a
"Sources" list. In `audit` mode, also check context7 / the web for newer guidance
and flag drift rather than trusting the doc blindly.

## How an agent should navigate a project built by this skill

1. Run `python tools/fn_search.py "<intent>"` (or read `FUNCTIONS.md`) to locate
   the function(s) to change — do this **before** reading source files.
2. Make the change; keep the Google-style docstring accurate.
3. Run `make functions-index` to refresh `FUNCTIONS.md` (CI fails on drift).
4. Add/extend deterministic tests for any non-LLM logic touched.
5. Run `make eval`; report the score delta.

## Recommended MCP servers

Wired into `templates/.mcp.json` by `skills/1-scaffold`; see
`references/mcp-catalogue.md` for rationale:

- **context7** — current library/framework docs (avoid stale API guesses).
- **playwright** — browser automation for web-interacting agents and dashboard E2E.
- **memory** — persistent knowledge-graph memory for the dev agent across sessions.
- **sequential-thinking** — structured multi-step reasoning for complex builds.
