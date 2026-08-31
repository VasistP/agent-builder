# Agent security standards (build + audit rubric)

_Last reviewed: 2026-08-29._

Mapped to the **OWASP Top 10 for Agentic Applications (2026)**. Same structure as
the other rubrics: **rule → why → how to verify → how to fix**. In `audit` mode,
also check for newer OWASP guidance and note drift.

**Why this is not optional for this framework's users.** OWASP ranks prompt
injection #1, present in **over 73% of systems audited in 2025**. The agentic
threat model is worse than the chatbot one: injection stops being a jailbreak and
becomes a way to *redirect decisions*. An agent that reads enterprise data and
holds tool access is the highest-risk profile there is — untrusted content
(retrieved rows, ticket bodies, documents, web pages) flows directly into a model
that can act.

The single most useful mental model: **the lethal trifecta** — private data +
untrusted content + an external communication channel. Any two are usually
manageable. All three in one agent means a successful injection can exfiltrate.
Check for the trifecta first; if present, break one leg of it.

---

## S0. The controls are wired, not merely present

Before auditing any individual control, check that it is on the path a real call
takes. A correct, unit-tested primitive that nothing calls is the most expensive
kind of security gap: it passes review, it passes tests, and it protects nothing.

- **Verify:** trace one side-effecting tool call end to end. Does the permission
  check run? Does the approval gate fire? Can a tool author actually *declare*
  the posture the enforcement reads — or does the declaration field exist with no
  way to set it? `make tools-posture` should list a non-empty set of
  approval-gated tools for any agent that writes anywhere.
- **Fix:** move enforcement to the narrowest chokepoint every call passes
  through (`dispatch`), make the declaration required rather than defaulted, and
  add a test that asserts a side-effecting tool is *denied* through the public
  path — not one that asserts the helper works in isolation.

## S1. All external content is treated as untrusted data, never as instructions
- **Why:** the model cannot reliably distinguish instructions in its prompt from
  instructions embedded in retrieved content. This is the root cause of #1.
- **Verify:** retrieved rows/documents/tool results are wrapped with explicit
  provenance markers and a standing instruction that content inside them is data
  to be analyzed, never commands to follow. Check `src/*/security/untrusted.py`.
- **Fix:** wrap at the boundary where content enters, not at the prompt template.

## S2. Tools are scoped to least privilege
- **Why:** "excessive agency" is its own OWASP category. An agent with a
  general-purpose SQL tool and write credentials can do anything the credentials
  allow, and injection inherits that power.
- **Verify:** every tool declares `side_effect` and `permission`. Read tools use
  read-only credentials. No general "execute arbitrary SQL/shell" tool exists
  unless explicitly justified in the spec and sandboxed.
- **Fix:** split broad tools into narrow ones with parameters; use a read-only DB
  role; scope credentials per tool, not per agent.

## S3. Side-effecting actions require an approval gate
- **Why:** deterministic enforcement is what makes agents safe, not better
  prompts. The model deciding to act is not the same as the action being allowed.
- **Verify:** tools with `side_effect=True` route through the approval gate in
  `src/*/agent/guardrails.py`; the gate is enforced in code, not in the prompt.
- **Fix:** wire the gate; default-deny anything unclassified.

## S4. The lethal trifecta is explicitly assessed
- **Why:** exfiltration requires an outbound channel. Removing it makes injection
  much less profitable even when it succeeds.
- **Verify:** `.agentbuilder/spec.md` records whether the agent has private data,
  untrusted input, and an outbound channel (email, HTTP, webhooks, writes to
  shared systems). If all three, a documented mitigation exists.
- **Fix:** remove the outbound channel, allowlist destinations, or require
  approval on every outbound action.

## S5. Memory and retrieved context cannot be poisoned persistently
- **Why:** "memory poisoning" is an OWASP category — content written into memory
  in one session steers behavior in later ones, turning a single injection into a
  persistent compromise.
- **Verify:** anything persisted to agent memory is attributed, and content that
  originated from untrusted sources is either not persisted or is marked and
  re-wrapped on read. Memory is scoped per tenant/user.
- **Fix:** attribute memory writes; never persist raw untrusted spans verbatim.

## S6. Tool output is validated before it re-enters the model
- **Why:** a compromised or buggy tool is an injection vector back into the loop.
- **Verify:** tool results are schema-checked and size-capped before being added
  to context.
- **Fix:** validate at the dispatch boundary in the tool registry.

## S7. Secrets never reach the model or the traces
- **Why:** anything in context can be echoed out; anything in traces can leak
  through a dashboard.
- **Verify:** credentials live in env/secret store and are used inside tools, not
  passed as tool arguments. Trace redaction is on (`observability` O6).
- **Fix:** move auth inside the adapter; add secret patterns to redaction.

## S8. Injection resistance is measured, not assumed
- **Why:** without eval cases you have no signal on whether a mitigation works or
  whether a prompt change silently removed it.
- **Verify:** `evals/` contains cases tagged `safety` with injected instructions
  in retrieved content, tool results, and conversation turns — asserting the
  agent does **not** follow them. Cross-reference `eval-standards.md` E12.
- **Fix:** add an injection slice derived from your real data sources.

## S9. Blast radius is bounded at runtime
- **Why:** even a correct agent misbehaves eventually; bounded damage is the
  difference between an incident and a catastrophe.
- **Verify:** per-request step, cost and time budgets; circuit breaker on
  repeated tool failures; rate limits on side-effecting tools.
- **Fix:** `src/*/agent/guardrails.py`.

## S10. Every action is attributable and auditable
- **Why:** enterprise compliance requires knowing which agent, on whose behalf,
  touched what data — and post-incident you need the reasoning chain.
- **Verify:** each action span records actor identity, target system, data
  accessed, and the conversation id. Retention meets the compliance window in
  `spec.md`.
- **Fix:** add identity attributes to spans; verify retention.

## S11. MCP servers and their tool metadata are vetted and pinned
- **Why:** **tool poisoning** — malicious instructions hidden in a tool's
  description or schema — is the highest-leverage attack on enterprise agents in
  2026, because that metadata is read by the model with more authority than
  retrieved data and is never seen by the human. An audit found **66% of scanned
  MCP servers had security findings**, and in February 2026 a trojanized server
  in a *legitimate registry* exfiltrated API keys and SSH keys.
- **Verify:** every entry in `.mcp.json` is version-pinned (never bare
  `npx -y pkg`), carries a vetting date, and passed the checklist in
  `references/mcp-catalogue.md`. Tool descriptions have actually been read.
  Credentials are scoped per server; no shared admin tokens. No general-purpose
  database MCP holds write access.
- **Fix:** pin every version, re-vet on bump, scope credentials down, and replace
  broad third-party servers with a narrow purpose-built one (`mcp-builder`).

---

## Audit output

Score each item `pass` / `partial` / `fail` / `n/a`, then rank the failures by
**exploitability × blast radius**, not by how easy they are to fix. State the
lethal-trifecta verdict first — it frames everything else.

## Sources
- OWASP — *Top 10 for Agentic Applications 2026* (prompt injection, insecure tool
  execution, excessive agency, memory poisoning).
- OWASP GenAI Security Project — *Exploit Round-up Q1 2026*.
- Lakera — *The Progressive Breach Model Behind the OWASP Top 10 for Agentic
  Applications*.
- arXiv 2604.12986 — *Parallax: Why AI Agents That Think Must Never Act*
  (separating reasoning from execution authority).
- arXiv 2606.26479 — *Adaptive Evaluation of Out-of-Band Defenses Against Prompt
  Injection in LLM Agents*.
- Checkmarx — *MCP Security: Risks, Real Incidents & Controls (2026)*.
- Cloud Security Alliance Labs — *MCP Tool Poisoning and IDE Auto-Execution* (2026).
- Microsoft Security — *The state of MCP security in 2026*.
