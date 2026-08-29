---
name: agent-builder-0-discovery
description: >-
  Phase 0 of agent-builder. Interview the user about the agent they want to
  build and write a structured spec to .agentbuilder/spec.md. Use at the start
  of a greenfield agent project.
---

# Phase 0 — Discovery

Goal: produce `.agentbuilder/spec.md`, a shared, reviewable description of the
agent. Do not write any code in this phase.

## Prerequisites / standalone notes

- None. Runs in an empty or existing directory.
- If `.agentbuilder/spec.md` already exists, read it and offer to revise rather
  than overwrite.

## Interview

Ask these in small batches (2–4 at a time), not all at once. Record answers as
you go. Push back on vague answers — ask for concrete examples.

### 1. Purpose & scope
- One sentence: what does the agent do for whom?
- 3–5 concrete example requests a user would make.
- 3 things it must explicitly *not* do (out of scope).
- Single-shot (one request → one answer) or conversational (multi-turn)? Both?

### 2. Users & interface
- Who uses it (role, technical level, internal/external)?
- Interface: API, chat UI, Slack, CLI, embedded in another app?
- Expected volume (requests/day) and concurrency.

### 3. Enterprise data
- What data sources does it read? (DBs, warehouses, docs, APIs, tickets…)
- For each: access method, auth, PII/sensitivity, size, update frequency.
- Does it write anywhere or take actions with side effects? List them.
- Retrieval needed (vector search)? Structured query (SQL)? Both?

### 4. Constraints
- Mandated framework / language / cloud (many enterprises fix this)? If yes, what?
- Latency budget (p50/p95).
- Cost ceiling per request, if any.
- Data residency / compliance (GDPR, HIPAA, SOC2, on-prem only…).
- Which model provider(s) are approved? Is a local model required?

### 5. Success criteria
- How will you know the POC worked? Define measurable pass bars.
- Top 3 failure modes you are worried about.
- Who signs off on each phase (the human in the checkpoint loop)?

### 6. Feature backlog
- List the features to build after the skeleton, roughly ordered. Each becomes
  one iteration of `skills/6-feature`.

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

Print the checkpoint block (see root `SKILL.md`). The user must read
`.agentbuilder/spec.md` and reply `approved`.
