---
name: agent-builder-7-security
description: >-
  Harden an AI agent against prompt injection, excessive agency, memory
  poisoning and unbounded blast radius, per the OWASP Top 10 for Agentic
  Applications. Has build / add / audit entry paths. Use when securing an agent
  that touches enterprise data or holds tool access, or when reviewing an
  existing agent's security posture.
---

# Phase 7 — Security hardening (non-negotiable for data/tool agents)

Goal: the agent still behaves correctly when its input is hostile. Read
`references/security-standards.md` first — it is the rubric, mapped to the OWASP
Top 10 for Agentic Applications (2026).

Runs after the skeleton (phase 5) and before or alongside the feature loop. For
an agent with **no tools and no external data**, this phase is light. For
anything reading enterprise data with tool access — the profile this framework
targets — it is mandatory.

## Entry paths

- **build** — greenfield: wire the boundaries into the skeleton.
- **add** — existing agent: instrument boundaries without redesigning it. Show a
  diff and get approval before applying.
- **audit** — score against `references/security-standards.md` S1–S10, check for
  newer OWASP guidance, output a prioritized gap list ranked by
  **exploitability × blast radius**. No changes unless asked.

## Start here: the lethal trifecta

Establish whether the agent has **private data + untrusted input + an external
channel**. All three means a successful injection can exfiltrate. State the
verdict plainly *before* discussing anything else and record it in the spec; if
present, break one leg rather than hardening the prompt.
→ `references/security-standards.md`

## Work, in order

1. **Untrusted boundaries (S1).** Every path where external content enters gets
   wrapped via `src/<pkg>/security/untrusted.py`. Wrap at the adapter or tool
   result — *not* in the prompt template, which is too easy to bypass by adding
   one more call site.
2. **Tool scoping (S2).** Give every tool an explicit `permission` and
   `side_effect`. Read tools get read-only credentials. Challenge any
   general-purpose "run arbitrary SQL/shell" tool — it is almost always the
   single largest risk in the system.
3. **Approval gates (S3).** Route `side_effect=True` tools through
   `require_approval`. It is default-deny, so a missing approver fails closed.
4. **Memory hygiene (S5).** Untrusted content must not be persisted verbatim
   into agent memory; a single injection would otherwise steer every later
   session. Scope memory per tenant/user.
5. **Blast radius (S9).** Set `Budgets` from the spec's latency and cost
   constraints. Wire the circuit breaker.
6. **Injection evals (S8).** Invoke `skills/3-evalset` to add a `safety` slice
   with injected instructions in retrieved content, tool results, and
   conversation turns — asserting the agent does **not** follow them. Derive
   these from the user's real data sources; generic examples miss the shapes
   that matter. This is the only evidence a mitigation actually works.
7. **MCP supply chain (S11).** Vet and pin every entry in `.mcp.json` against
   the checklist in `references/mcp-catalogue.md`. Read the tool descriptions —
   poisoning hides there and is invisible in normal use. Confirm no database MCP
   holds write credentials.
8. **Run the `security-review` skill** over the diff. It complements this rubric
   with a real review of the changed code; don't reimplement diff scanning here.
9. **Attribution (S10).** Actor identity, target system, and data accessed on
   every action span. Confirm retention meets the compliance window in the spec.

## Working with the user

Ask, don't assume:
- Which data sources contain content authored by someone outside your company?
- What is the worst thing this agent could do with its current credentials?
- Who is allowed to approve a side-effecting action, and how are they reached?
- What is the compliance retention requirement for the audit trail?

Report findings by risk, not by effort. If the honest answer is "a successful
injection here could exfiltrate the customer table", say exactly that.

## Checkpoint

Checkpoint block. Verify: trifecta verdict recorded; `make test` green including
the security suite; injection eval cases present and passing; a side-effecting
tool demonstrably blocked without an approver. User replies `approved`.
