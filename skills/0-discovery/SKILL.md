---
name: agent-builder-0-discovery
description: >-
  Phase 0 of agent-builder. Rigorously interview the user about the agent they
  want to build — questions in small batches, consensus before anything is
  written — then record the agreed spec in .agentbuilder/spec.md. Use at the
  start of a greenfield agent project.
---

# Phase 0 — Discovery

Goal: produce `.agentbuilder/spec.md`, a shared, reviewable description of the
agent. Do not write any code in this phase.

## Prerequisites / standalone notes

- None. Runs in an empty or existing directory.
- If `.agentbuilder/spec.md` already exists, read it and offer to revise rather
  than overwrite.

## This phase is an interview, not a document

**Do not draft `spec.md` and ask the user to check it.** That is the one thing
this phase must not do — a skimmed document locks in guesses that phase 3 then
encodes as ground truth. Read `references/interview-protocol.md` before you
start; it is binding here.

Also print the session opener from the root `SKILL.md` first, so the user knows
the interaction style, which defaults are already locked, and what
`skills/override` can change.

Only `interaction.interview_mode` (Tier B override) permits the document-first
flow. Short answers, impatience, or "you decide" do not.

## Interview

Ask these in small batches (2–4 at a time), **never as a list**. Record answers
as you go and let each answer reshape the next question. Push back on vague
answers — ask for the number, the table name, the actual example. Anything the
user genuinely does not know becomes a recorded assumption, not an invention.

### 1. Purpose & scope
- One sentence: what does the agent do for whom?
- 3–5 concrete example requests a user would make.
- 3 things it must explicitly *not* do (out of scope).
- Single-shot (one request → one answer) or conversational (multi-turn)? Both?

### 1b. Is an agent even the right architecture?

Ask this before anything else, and be willing to talk the user out of an agent.
The most reliable production systems separate orchestrated **workflows** from
autonomous **agents**, and use the latter only when the task genuinely requires
open-ended reasoning.

- Can you write down the steps in advance? → a **workflow** with an LLM in one or
  two nodes is cheaper, faster, testable, and far more reliable.
- Does the path genuinely branch on content the model must interpret, in ways you
  cannot enumerate? → an **agent** is justified.
- Somewhere between? → a workflow with one agentic step, not a fully autonomous
  agent.

Record the verdict and the reasoning in the spec. If a workflow suffices, say so
plainly — building an agent where a pipeline would do is the most expensive
mistake available at this stage, and it is made before any code exists.

### 2. Users & interface
- Who uses it (role, technical level, internal/external)?
- Interface: API, chat UI, Slack, CLI, embedded in another app?
- Expected volume (requests/day) and concurrency.

### 3. Enterprise data
- What data sources does it read? (DBs, warehouses, docs, APIs, tickets…)
- For each: access method, auth, PII/sensitivity, size, update frequency.
- Does it write anywhere or take actions with side effects? List them.
- Retrieval needed (vector search)? Structured query (SQL)? Both?

### 3b. Security posture — the lethal trifecta

Establish whether the agent will have all three of: private data, untrusted input
(any content it did not author — retrieved rows, documents, tickets, web pages),
and an external communication channel. All three together mean a successful
prompt injection can exfiltrate. Record the verdict; `skills/7-security` acts on
it. See `references/security-standards.md`.

### 4. Constraints
- Mandated framework / language / cloud (many enterprises fix this)? If yes, what?
- Latency budget (p50/p95).
- Cost ceiling per request, if any.
- Data residency / compliance (GDPR, HIPAA, SOC2, on-prem only…). Record these
  to inform design — whether to enable trace content capture, where data may
  live, what the agent must refuse. This framework does **not** implement
  compliance machinery; say so plainly rather than letting the user assume it
  is covered.
- Which model provider(s) are approved? Is a local model required?

### 5. Success criteria
- How will you know the POC worked? Define measurable pass bars.
- Top 3 failure modes you are worried about.
- Who signs off on each phase (the human in the checkpoint loop)?

### 6. Feature backlog
- List the features to build after the skeleton, roughly ordered. Each becomes
  one iteration of `skills/6-feature`.

## Consensus check — before writing anything

When the interview is done, issue the consensus check block from
`references/interview-protocol.md`: a numbered read-back of every decision, the
assumptions you made where the user didn't specify, and what is still open. Wait
for `agreed`.

Be explicit about the two conclusions that are easiest to nod through and most
expensive to get wrong: the **agent-vs-workflow verdict** (§1b) and the
**trifecta verdict** (§3b). State each in one plain sentence and ask the user to
confirm it directly.

`.agentbuilder/spec.md` is written *after* `agreed`. It is a record of the
conversation, not a proposal.

## Output: `.agentbuilder/spec.md`

Use this template:

```markdown
# Agent Spec — <name>
_Last updated: <date> · Owner: <user> · Sign-off: <name(s)>_

## Purpose
<one sentence>

## Example requests
- ...

## Out of scope
- ...

## Interaction model
Single-shot | Conversational | Both — <notes>

## Users & interface
...

## Data sources
| Source | Access | Auth | Sensitivity | Read/Write | Notes |
|--------|--------|------|-------------|-----------|-------|

## Actions with side effects
- ...

## Constraints
- Framework/lang/cloud: ...
- Latency: p50 <x> / p95 <y>
- Cost ceiling: ...
- Compliance: ...
- Approved models: ... (local required? yes/no)

## Agent type (for observability + eval defaults)
<one of: single-shot Q&A · RAG · tool/workflow · multi-agent · conversational assistant>
Rationale: ...

## Success criteria (measurable)
- ...

## Feared failure modes
1. ...

## Feature backlog
1. ...
```

The **agent type** line drives defaults in later phases — pick it explicitly with
the user.

## Checkpoint

Print the checkpoint block (see root `SKILL.md`). This is a second, separate
gate from the consensus check: consensus was "did I understand you", the
checkpoint is "is the written spec acceptable". The user must read
`.agentbuilder/spec.md` and reply `approved`.
