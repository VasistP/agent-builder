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

**Interview required — this phase is locked to it.** Ask about the trifecta
verdict, which tools are genuinely side-effecting, and who approves what. Small
batches, then a consensus check the user accepts *before* you write or generate
anything. Only a completed run of `skills/override` lifts this; the word
"override" typed here does not. → `references/interview-protocol.md`

Runs after the skeleton (phase 5) and before or alongside the feature loop. For
an agent with **no tools and no external data**, this phase is light. For
anything reading enterprise data with tool access — the profile this framework
targets — it is mandatory.

## Entry paths

- **build** — greenfield: wire the boundaries into the skeleton.
- **add** — existing agent: instrument boundaries without redesigning it. Show a
  diff and get approval before applying.
- **audit** — score against `references/security-standards.md` S1–S11, check for
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
7. **MCP supply chain (S11).** `make integrations` to see what is actually
   enabled, then vet each entry in `.mcp.json` against
   `references/mcp-catalogue.md`. Read the tool descriptions — poisoning hides
   there and is invisible in normal use. Confirm no database MCP holds write
   credentials, and that nothing uncatalogued crept in.
8. **Review the changed code** — via the `security-review` skill if available,
   otherwise walk the diff against S1–S11 by hand, ranked by exploitability x
   blast radius.
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

## Then hand off to phase 8

This phase builds the controls; `skills/8-adversarial` tests whether they hold.
Do not treat hardening as verified until the red-team suite has run — an
untested control is a hypothesis.


## Tool posture — declared, enforced, and visible

Every tool must declare a permission; there is no default. The decorator raises
at import time if one is missing, listing the options, because a tool nobody
classified would otherwise register as read-only while holding whatever its
credentials allow.

```bash
make tools-posture     # every tool: permission, side-effect flag, file:line
```

Walk that table with the user, tool by tool. The report names the declaration
site so a wrong answer is a one-line edit, and it flags two mistakes on its own:
a `delete_*`/`send_*` tool declared READ, and a WRITE/EXTERNAL tool marked
`side_effect=False` (which would bypass the approval gate).

Both controls are enforced in `dispatch()` — the single chokepoint every tool
call passes through — not in the graph node, so a call path added later cannot
bypass them. Order is permission first, then approval: an ungranted tool is
refused before a human ever sees its arguments, so the approval prompt cannot be
used as an exfiltration channel.

Grants and the approver come from `RunPolicy`. The default is READ-only with no
approver, so **an unattended run cannot take an irreversible action**. Eval runs
use `deny_all` deliberately: if evals auto-approved, an adversarial case
asserting `no_side_effects` would either pass for the wrong reason or actually
perform the side effect while red-teaming.

Demonstrate the checkpoint requirement concretely:

```python
dispatch("<a side-effecting tool>", {...}, granted={Permission.EXTERNAL})
# ApprovalRequired — the gate fired
```

## Checkpoint

Checkpoint block. Verify: trifecta verdict recorded; `make test` green including
the security suite; injection eval cases present and passing; a side-effecting
tool demonstrably blocked without an approver. User replies `approved`.
