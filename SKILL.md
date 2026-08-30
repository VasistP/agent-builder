---
name: agent-builder
description: >-
  Interactive, checkpoint-gated framework for standing up a production-grade
  enterprise AI-agent POC. Use when someone wants to start a new agent project,
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
   noise band aren't signal; the gate is pass^k. A **golden standard** of 20
   single / 5 conversations / 12 adversarial (every attack class covered or
   waived) / 3 multi-turn adversarial is stated to the user, never asked of them,
   and enforced by `make eval-coverage`. → `references/eval-standards.md`
9. **API keys need explicit permission.** Judge defaults to local Ollama; warn
   that a hosted judge costs money per run.
10. **Interview-locked phases: 0, 3, 6, 7, 8.** Their inputs exist only in the
   user's head. Never write a spec, eval case, acceptance criterion or threat
   model and ask them to review it — ask, reach a consensus check, *then* write.
   → `references/interview-protocol.md`

## Interaction mode — interview where it's load-bearing

| Phases | Mode | Why |
|--------|------|-----|
| **0, 3, 6, 7, 8** | **`interview` — locked** | the answer exists only in the user's head: purpose, a case's ground truth, a feature's acceptance criteria, which tools truly have side effects, what counts as a breach here. Guess it and the guess becomes the ground truth everything downstream is measured against |
| 1, 2, 4, 5 | `propose` | the framework already has a defensible default, so hand the user something concrete to correct rather than a blank to fill |

**In an interview-locked phase**: questions 2–4 at a time, never a list, push back
on vague answers, and close with a consensus check the user accepts before
anything is written to disk. Writing the document first and asking "does this look
right?" is not permitted — people skim, and the nuance lost is exactly the
expensive kind. → `references/interview-protocol.md`

**In a `propose` phase**: state the defaults you intend to apply and the one or
two real choices, get an explicit yes, then build. Still no silent decisions —
just no consensus-check ceremony.

Turning an interview off — for one phase or all of them — requires **running
`skills/override`**. Typing the word "override" at a phase skill does nothing;
neither do impatience, terse answers, or "just do it". Those mean ask fewer,
better questions.

## Session opener — print this first

Before phase 0, or any standalone/targeted run, print the **"Good to know"**
orientation block verbatim from `references/interview-protocol.md` § *Session
opener*: how the session runs, the defaults already locked, what `skills/override`
can change and at what ceremony, and what is out of scope. Skip it only if
`.agentbuilder/` already exists — then summarize current mode and active
overrides instead.

## Scope — and what this deliberately does not do

This framework covers **building the agent, evaluating it, and observing it**.
That includes the security and adversarial phases, because injection resistance
is an evaluation problem and blast-radius control is an implementation one.

It does **not** cover, and should not grow to cover:

- regulatory compliance (EU AI Act classification, audit evidence, incident
  reporting), data governance, retention or right-to-erasure
- per-user data authorization / ACL-aware retrieval
- production deployment, environment promotion, or secrets management

These are real and often mandatory for enterprise agents — they belong to
whoever owns compliance and platform, not here. When discovery surfaces one,
**name it as out of scope and move on**; don't build it, and don't quietly leave
the user thinking it's handled.

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
| **full** | greenfield | phases 0 → 8 in order |
| **targeted** | "just evals" / "just observability" / "just security" / "red-team it" | that sub-skill only, against the existing repo — never re-scaffold, never touch agent logic |
| **audit** | "review our existing setup" | sub-skill(s) in `audit` path: score against the matching `*-standards.md`, output prioritized gaps + effort |

Resume from `.agentbuilder/progress.md` if present.

## Phases

| # | Sub-skill | Checkpoint |
|---|-----------|-----------|
| 0 | `0-discovery` → `.agentbuilder/spec.md` (interview) | user confirms the spec |
| 1 | `1-scaffold` → skeleton, tooling, context files, integration catalogue | `make setup && make test` green |
| 2 | `2-observability` → spans, dashboard, JSON export | a trace from a smoke call |
| 3 | `3-evalset` → Tier 1 eval sets, judge (interview) | `make eval` runs |
| 4 | `4-testing` → deterministic suites | green, zero tokens |
| 5 | `5-agent-skeleton` → minimal agent loop | one traced call; baseline eval |
| 6 | `6-feature` (repeat) → one feature per run (interview) | eval delta + approval |
| 7 | `7-security` → boundaries, scoping, injection evals (interview) | trifecta verdict; a side-effecting tool demonstrably blocked |
| 8 | `8-adversarial` → red-team corpus + live session (interview) | golden standard met (`make eval-coverage-golden`); zero breaches, or accepted risks signed off |

Phases 7–8 are mandatory for any agent reading enterprise data with tool access.
Phase 7 builds the defenses; phase 8 assumes they're wrong and tries to break
them. **An adversarial breach is never noise** — the noise band does not apply,
and a single breach fails the build.

## Checkpoint protocol

Two gates per phase, and they are not the same thing. The **consensus check**
comes first — before anything is written — and confirms you understood the user
(`references/interview-protocol.md`). The **checkpoint** comes last and confirms
the work is acceptable. Never collapse them into one.

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
| red-teaming | `adversarial-standards.md` |
| writing tests | `deterministic-testing.md` |
| ordering test/eval/implement | `methodology.md` |
| context files + model routing | `context-and-cost.md` |
| tool catalogue, compaction, multi-agent | `tool-design.md` |
| choosing a framework | `stack-options.md` |
| MCP vetting + companion skills | `mcp-catalogue.md` |
| how to run any phase's interview | `interview-protocol.md` |
| any override request | `override-registry.md` |

Standards docs carry a "Last reviewed" date. In `audit` mode, check for newer
guidance and flag drift rather than trusting them blindly.
