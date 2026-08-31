---
name: agent-builder
description: >-
  Interactive, checkpoint-gated framework for standing up a rigorously
  evaluated enterprise AI-agent POC. Use when someone wants to start a new agent project,
  or wants to add/audit evaluations, observability or security on an existing
  agentic codebase. Walks through discovery, scaffolding, observability, eval
  test-set creation, deterministic testing, an agent skeleton, an eval-gated
  feature loop, and security hardening. Runs as a rigorous interview by
  default — questions and consensus first, documents afterwards. Evals and
  observability are non-negotiable.
---

# agent-builder

Builds the *environment* for an enterprise AI agent before any agent logic
exists, then drives feature work through an eval-gated loop with a **mandatory
human checkpoint between every phase**.

This file is the router: it loads on every invocation, so it holds procedure
only. The reasoning for each rule is in the reference it points to — read that
when you work the phase, not before.

## Non-negotiables

1. **Evals and observability are always set up.** Not skippable from any skill.
2. **No fabricated model calls.** → `deterministic-testing.md`
3. **Observability always writes portable OTel-GenAI JSON.** → `observability-standards.md`
4. **Human checkpoint between phases.** Wait for `approved`.
5. **TDD for deterministic code, tiered EDD for model behavior.** → `methodology.md`
6. **Context files are mandatory**: `AGENTS.md`, `docs/ARCHITECTURE.md`,
   append-only `CHANGELOG`/`TODO`, model-tier routing. → `context-and-cost.md`
7. **Security for any data/tool agent.** → `security-standards.md`
8. **Evals measure reliability, not one sample.** 3+ runs/case, gate on pass^k.
   The golden standard (20 single / 5 conversations / 12 adversarial / 3
   multi-turn) is a **coverage floor, stated to the user rather than asked of
   them**, enforced by `make eval-coverage`. It is not statistical power: at
   n=20 the 95% margin of error is ±22pp, so report *which cases flipped*, never
   a few-point aggregate move. → `eval-standards.md`
9. **API keys need explicit permission.** Judge defaults to local Ollama; a
   hosted judge costs money per run — say so before enabling one.
10. **Phases 0, 3, 6, 7, 8 are interview-locked.** → `interview-protocol.md`

## Interaction mode

| Phases | Mode | Do |
|--------|------|-----|
| **0, 3, 6, 7, 8** | `interview` — locked | 2–4 questions at a time, never a list; push back on vague answers; close with a consensus check the user accepts **before** anything is written to disk |
| 1, 2, 4, 5 | `propose` | state the defaults you'll apply and the one or two real choices, get an explicit yes, then build |

A locked phase may not write a document and ask "does this look right?".
Unlocking one requires **running `skills/override`**; the word "override" typed
at a phase skill does nothing, and impatience or "just do it" are not overrides.

Before phase 0, or any standalone/targeted run, print the **"Good to know"**
block verbatim from `interview-protocol.md` § *Session opener* — skip it only if
`.agentbuilder/` exists, then summarize current mode and active overrides.

## Scope

Covers **building, evaluating and observing** the agent, security and
adversarial testing included. Does **not** cover regulatory compliance and data
governance, per-user data authorization / ACL-aware retrieval, or deployment and
secrets management — those belong to whoever owns compliance and platform. When
discovery surfaces one, **name it as out of scope and move on**: don't build it,
and don't leave the user thinking it's handled.

## Everything is locked — `skills/override` is the only key

No skill may change any default in `override-registry.md`, routine config
included. When asked to skip, disable, replace or reconfigure something:

> That's a locked default. I can't change it from here — run `skills/override`
> and I'll assess what it would cost *in this repo*, show you the alternatives,
> and record the decision.

Then stop — don't pre-assess, don't pre-argue, don't treat the request as
consent. Read `.agentbuilder/overrides.md` at the start of every run.

## Modes — ask first

| Mode | When | What runs |
|------|------|-----------|
| **full** | greenfield | phases 0 → 8 in order |
| **targeted** | "just evals" / "just security" / "red-team it" | that sub-skill only, against the existing repo — never re-scaffold, never touch agent logic |
| **audit** | "review our existing setup" | sub-skill(s) in `audit` path: score against the matching `*-standards.md`, output prioritized gaps + effort |

Resume from `.agentbuilder/progress.md` if present. If the user is unsure where
they are or what to do next, run `skills/help` — it reads the project's real
state and returns one concrete next step.

## Phases

| # | Sub-skill | Checkpoint |
|---|-----------|-----------|
| 0 | `0-discovery` → `.agentbuilder/spec.md` · interview | user confirms the spec |
| 1 | `1-scaffold` → skeleton, tooling, context files, integrations | `make setup && make test` green |
| 2 | `2-observability` → spans, dashboard, JSON export | a trace from a smoke call |
| 3 | `3-evalset` → Tier 1 eval sets, judge · interview | `make eval-coverage` clears 6 / 2 |
| 4 | `4-testing` → deterministic suites | green, zero tokens |
| 5 | `5-agent-skeleton` → minimal agent loop | one traced call; baseline eval |
| 6 | `6-feature` (repeat) → one feature per run · interview | eval delta + approval |
| 7 | `7-security` → boundaries, scoping, injection evals · interview | trifecta verdict; a side-effecting tool demonstrably blocked |
| 8 | `8-adversarial` → red-team corpus + live session · interview | `make eval-coverage-golden` passes; zero breaches, or accepted risks signed off |

Phases 7–8 are mandatory for any agent reading enterprise data with tool access.
**An adversarial breach is never noise** — one breach fails the build.
→ `adversarial-standards.md`

## Checkpoint protocol

Two gates per phase, never collapsed: the **consensus check** comes first,
before anything is written, and confirms you understood the user; the
**checkpoint** comes last and confirms the work is acceptable.

End every phase with exactly this, then update `.agentbuilder/progress.md` and
stop:

```
### Checkpoint: phase <n> — <name>
Done: <bullets>
Verify yourself: <commands>
Open risks / decisions: <bullets or "none">

Reply `approved` to continue to phase <n+1>, or tell me what to change.
```

## External skills and MCPs — on demand, never bundled

Projects ship a catalogue (`.agent/integrations.yml`) and a checker, not a
pre-filled `.mcp.json`. Run `make integrations`, show what each would unlock,
enable only what the user asks for. Uncatalogued servers are unvetted — adding
one is a Tier B override. → `mcp-catalogue.md`

Companion skills are used **if available**, never required. Built-ins aren't
visible on disk, so check your own skill listing and fall back to the manifest
rather than skipping a step: `dataviz` (dashboard charts), `code-review`
(feature checkpoint), `security-review` (phase 7), `claude-api` (model ids,
pricing), `mcp-builder` (custom servers).

## Reference index — read on demand, not upfront

Paths are relative to `references/`.

- running an interview-locked phase → `interview-protocol.md`
- evals → `eval-standards.md`, `eval-authoring-guide.md`
- observability → `observability-standards.md`, `observability-options.md`
- security → `security-standards.md` · red-teaming → `adversarial-standards.md`
- deterministic tests → `deterministic-testing.md`
- ordering test/eval/implement → `methodology.md`
- context files + model routing → `context-and-cost.md`
- tool catalogue, compaction, multi-agent → `tool-design.md`
- choosing a framework → `stack-options.md`
- MCP vetting + companion skills → `mcp-catalogue.md`
- any override request → `override-registry.md`

Standards docs carry a "Last reviewed" date; in `audit` mode, check for newer
guidance and flag drift.
