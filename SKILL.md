---
name: agent-builder
description: >-
  Interactive, checkpoint-gated framework for standing up a production-grade
  enterprise AI-agent POC. Use when someone wants to start a new agent project,
  or wants to add/audit evaluations, observability or security on an existing
  agentic codebase. Walks through discovery, scaffolding, observability, eval
  test-set creation, deterministic testing, an agent skeleton, an eval-gated
  feature loop, and security hardening. Evals and observability are
  non-negotiable.
---

# agent-builder

Builds the *environment* for an enterprise AI agent before any agent logic
exists, then drives feature work through an eval-gated loop with a **mandatory
human checkpoint between every phase**.

## Non-negotiables

1. **Evals and observability are always set up.** Not skippable from any skill.
2. **No fabricated model calls.** Deterministic tests cover non-LLM code only;
   model behavior is measured by evals. → `references/deterministic-testing.md`
3. **No vendor lock-in.** Observability always writes portable OTel-GenAI JSON
   traces. → `references/observability-standards.md`
4. **Human checkpoint between phases.** Wait for `approved` before continuing.
5. **Test-first, split by determinism.** Strict TDD for deterministic code;
   tiered EDD for model behavior. → `references/methodology.md`
6. **Context files are mandatory.** `AGENTS.md`, `docs/ARCHITECTURE.md` (snapshot),
   `CHANGELOG`/`TODO` (append-only), model-tier routing.
   → `references/context-and-cost.md`
7. **Security for any data/tool agent.** Untrusted-content boundaries,
   least-privilege tools, approval gates, injection evals.
   → `references/security-standards.md`
8. **Evals measure reliability, not one sample.** 3+ runs/case; deltas inside the
   noise band aren't signal; the gate is pass^k. → `references/eval-standards.md`
9. **API keys need explicit permission.** Judge defaults to local Ollama; warn
   that a hosted judge costs money per run.

## Everything is locked — `skills/override` is the only key

No skill may change any default in `references/override-registry.md`, including
routine config. When asked to skip, disable, replace or reconfigure something:

> That's a locked default. I can't change it from here — run `skills/override`
> and I'll assess what it would cost *in this repo*, show you the alternatives,
> and record the decision.

Then stop. Don't pre-assess, don't pre-argue, don't treat the request as consent.
Read `.agentbuilder/overrides.md` at the start of every run — it says which
guarantees are currently off.

## Modes — ask first

| Mode | When | What runs |
|------|------|-----------|
| **full** | greenfield | phases 0 → 7 in order |
| **targeted** | "just evals" / "just observability" / "just security" | that sub-skill only, against the existing repo — never re-scaffold, never touch agent logic |
| **audit** | "review our existing setup" | sub-skill(s) in `audit` path: score against the matching `*-standards.md`, output prioritized gaps + effort |

Resume from `.agentbuilder/progress.md` if present.

## Phases

| # | Sub-skill | Checkpoint |
|---|-----------|-----------|
| 0 | `0-discovery` → `.agentbuilder/spec.md` | user confirms the spec |
| 1 | `1-scaffold` → skeleton, tooling, context files, integration catalogue | `make setup && make test` green |
| 2 | `2-observability` → spans, dashboard, JSON export | a trace from a smoke call |
| 3 | `3-evalset` → Tier 1 eval sets, judge | `make eval` runs |
| 4 | `4-testing` → deterministic suites | green, zero tokens |
| 5 | `5-agent-skeleton` → minimal agent loop | one traced call; baseline eval |
| 6 | `6-feature` (repeat) → one feature per run | eval delta + approval |
| 7 | `7-security` → boundaries, scoping, injection evals | trifecta verdict; a side-effecting tool demonstrably blocked |

Phase 7 is mandatory for any agent reading enterprise data with tool access.

## Checkpoint protocol

End every phase with exactly this, then update `.agentbuilder/progress.md` and
stop:

```
### Checkpoint: phase <n> — <name>
Done: <bullets>
Verify yourself: <commands>
Open risks / decisions: <bullets or "none">

Reply `approved` to continue to phase <n+1>, or tell me what to change.
```

## External skills and MCPs — checked, then installed on demand

**Nothing is bundled.** Projects ship a catalogue (`.agent/integrations.yml`) and
a checker, not a pre-filled `.mcp.json`. Run `make integrations`, show the user
what each would unlock, and enable only what they ask for — every added server
widens the supply chain and more tools degrade selection accuracy.

Skills are used **if available**, never required: built-ins aren't visible on
disk, so check your own skill listing and use the manifest's fallback when one is
missing rather than skipping the step. `dataviz` for dashboard charts,
`code-review` at the feature checkpoint, `security-review` in phase 7,
`claude-api` for model ids and pricing, `mcp-builder` for custom internal servers.

Anything uncatalogued is unvetted; adding it is a Tier B override.
→ `references/mcp-catalogue.md`

## Reference index — read on demand, not upfront

| Read when | File |
|-----------|------|
| building/auditing evals | `eval-standards.md`, `eval-authoring-guide.md` |
| building/auditing observability | `observability-standards.md`, `observability-options.md` |
| building/auditing security | `security-standards.md` |
| writing tests | `deterministic-testing.md` |
| ordering test/eval/implement | `methodology.md` |
| context files + model routing | `context-and-cost.md` |
| tool catalogue, compaction, multi-agent | `tool-design.md` |
| choosing a framework | `stack-options.md` |
| MCP vetting + companion skills | `mcp-catalogue.md` |
| any override request | `override-registry.md` |

Standards docs carry a "Last reviewed" date. In `audit` mode, check for newer
guidance and flag drift rather than trusting them blindly.
