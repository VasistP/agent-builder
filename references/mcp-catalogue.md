# MCP servers and companion skills

_Last reviewed: 2026-08-29._

Two parts: a **mandatory vetting standard** for any MCP server entering a
project, and the **curated set** this framework offers. Nothing is installed by
default — the scaffold ships a catalogue and a checker, and you enable what you
need. Adding an unvetted server is a Tier B override.

---

## Why vetting is mandatory here

The MCP ecosystem passed **17,000 public servers**, and an audit found
**66% of scanned servers had security findings**. Most are toys, abandoned
experiments, or actively dangerous.

The attack that matters most is **tool poisoning**: malicious instructions hidden
in a tool's *description or schema* — metadata the model reads and the human
never sees. It is now described as the highest-leverage attack on enterprise AI
agents, because tool descriptions carry more authority with the model than
retrieved data does.

In **February 2026** the SmartLoader operation published a trojanized Oura Ring
MCP server to a legitimate registry, functionally identical to the real one,
carrying an infostealer that exfiltrated browser passwords, cloud session tokens,
SSH keys, and API keys. A single compromised repository propagates to every
developer who opens it.

This framework recommends MCP servers, which makes it part of your supply chain.
Hence the gate.

## Vetting checklist — every server, before it enters `.mcp.json`

- [ ] **Provenance.** Official vendor or a repo you can name a maintainer for.
      Registry presence proves nothing — SmartLoader was *in* a legitimate registry.
- [ ] **Maintained.** Commits in the last ~6 months; issues answered.
- [ ] **Version pinned.** Never `npx -y pkg` bare — that installs latest,
      unreviewed, on every launch. Pin exactly.
- [ ] **Tool descriptions read.** Actually read them. This is where poisoning
      hides, and it is invisible in normal use.
- [ ] **Least privilege.** Credentials scoped to what it needs; read-only where
      possible. Never a shared admin token.
- [ ] **Blast radius understood.** What can it reach — filesystem, network,
      production data? Write it down.
- [ ] **Sandboxed if local.** Local servers run with your user's privileges.
- [ ] **Change detection.** The pin is the mechanism: a changed tool definition
      shows up as a diff to `.mcp.json` rather than arriving silently.
- [ ] **Re-vetted on version bump.** A bump is a new supply-chain event.

Record the vetting date in the `//` comment next to each server.

## Treat MCP tool metadata as untrusted

Cross-reference `references/security-standards.md` **S11**. Tool descriptions
enter the model's context with high authority. Sourcing a tool from outside your
organization means importing text you did not write into a privileged position.
Read it, pin it, and scope the credentials accordingly.

---

## The curated set

**Nothing here is installed by default.** The scaffold ships no `.mcp.json` — it
ships `.agent/integrations.yml` (this catalogue, machine-readable) plus
`tools/check_integrations.py`. Run `make integrations` to see what is present and
what each would unlock; enable individually with
`make integrations-enable NAME=<x>`.

Deliberately small: more tools measurably *hurt* selection accuracy (see
`references/tool-design.md`), and every added server widens the supply chain.
Enabling on demand keeps both costs proportional to what you actually use.

| MCP | Purpose | Risk notes |
|-----|---------|-----------|
| **context7** | Current library/framework docs, so the agent stops guessing stale APIs | Read-only, no repo access. Lowest-risk of the four. |
| **playwright** | Browser automation: dashboard E2E, web-interacting agents | Reaches arbitrary URLs. Page content is untrusted input (S1). |
| **memory** | Cross-session knowledge graph for the dev agent | Persists model-authored content — see S5 on memory poisoning. Do not persist untrusted spans verbatim. |
| **sequential-thinking** | Structured multi-step reasoning for complex planning | No I/O; minimal surface. |

### Conditional — added only after discovery picks the data layer

Do **not** preinstall a database MCP. Once `.agentbuilder/spec.md` names concrete
stores, `skills/1-scaffold` adds *one* matching server, vetted, with a **read-only
role**. A general-purpose database MCP holding write credentials is the single
largest excess-agency risk you can add to an enterprise agent — it hands a
successful prompt injection your whole schema.

If nothing off-the-shelf fits your internal systems, build one — see
`mcp-builder` below. A narrow, purpose-built server you control beats a broad
third-party one.

### Deliberately not included

| Server | Why not |
|--------|---------|
| GitHub MCP | The `gh` CLI is already available, already authenticated, and adds no new supply chain. |
| Filesystem MCP | Coding agents already have file tools; this duplicates them with a wider surface. |
| Sentry / hosted APM | Conflicts with the OSS-only, self-hostable observability stance (`observability-options.md`). |
| "Everything" / aggregator servers | Maximum surface, minimum scrutiny — the opposite of the subtraction principle. |

---

## Companion skills

This framework should **compose with** existing skills rather than reimplement
them. Where a good skill already exists, invoke it.

| Skill | Used by | Why |
|-------|---------|-----|
| **dataviz** | `skills/2-observability` | The dashboard builds charts. Use it before writing chart code — it covers palette, accessibility, and dashboard layout properly. |
| **security-review** | `skills/7-security` | Runs a real review over the diff. Complements the S1–S11 rubric; do not reimplement diff scanning. |
| **code-review** | `skills/6-feature` | The pre-merge checkpoint is exactly its use case. |
| **claude-api** | `skills/3-evalset`, `evals/pricing.json` | Authority for current model IDs, pricing, and limits. `pricing.json` goes stale otherwise — never fill it from memory. |
| **mcp-builder** (official) | `skills/1-scaffold`, `skills/6-feature` | The sanctioned way to build a custom MCP server for an internal system. Preferred over adopting a broad third-party server. |
| **skill-creator** (official) | after the POC | Turns your team's conventions — release process, review checklist, data-access policy — into reusable skills. The natural next step once the agent stabilizes. |

Guidance from the ecosystem: **8–12 well-chosen skills** cover most of a senior
developer's day, and the safest starting point is an official skill or a narrowly
scoped community one. The same subtraction principle that applies to agent tools
applies here.

---

## Sources
- Checkmarx — *MCP Security: Risks, Real Incidents & Controls (2026)* (SmartLoader).
- Cloud Security Alliance Labs — *MCP Tool Poisoning and IDE Auto-Execution* (2026).
- Practical DevSecOps — *MCP Security Vulnerabilities* and *MCP Security Statistics 2026*.
- Microsoft Security — *The state of MCP security in 2026*.
- UpGuard — *Six MCP Security Incidents Every Security Leader Should Know*.
- Toolradar / Builder.io / Firecrawl — best-MCP-server surveys, 2026.
- Firecrawl, Developers Digest — Claude Code skills directories, 2026.
