# Tool design and runtime context management

_Last reviewed: 2026-08-29._

Two areas with unusually high return per hour spent, both under-served by the
attention normally given to prompts and model choice.

---

## Tool design

**The headline finding, repeated across independent sources: improving tool
descriptions and removing redundancy moved agent reliability more than switching
to a more capable base model.** Tool design is upstream of prompt tuning, and it
is cheaper.

### The subtraction principle

Performance rises as you add the first few relevant tools, **plateaus, then
declines** as the catalogue keeps growing. Studies of tool-calling across long
contexts show accuracy dropping substantially as catalogue size increases — even
with 128K windows, because the problem is selection, not context length. Vercel's
sales agent improved measurably after deleting the majority of its tools.

**Overlap hurts more than raw count.** Teams successfully run 15+ well-separated
tools while others struggle with fewer than 10 overlapping ones. Three database
retrieval tools should usually be one tool with parameters — that removes choice
paralysis without removing capability.

`audit_tools()` in `src/<pkg>/tools/registry.py` checks catalogue size, thin
descriptions, missing parameter schemas, and name-token overlap. Run it at every
feature checkpoint.

### What makes a tool description good

Three things determine whether a tool works, and all are authored, not learned:

| Element | Determines |
|---------|-----------|
| **Description** | whether the model knows *when and why* to reach for it |
| **Parameter schema** | whether it can invoke it *correctly* |
| **Error signaling** | whether it can *recover* from a failed invocation |

Write the description for a reader who cannot see the implementation. State when
to use it, when *not* to, and what it returns. A tool whose description could
plausibly describe a sibling tool will be confused with it.

Error messages are part of the interface: `"invalid date"` teaches nothing, while
`"start_date must be ISO-8601 (YYYY-MM-DD); got '03/2026'"` lets the agent fix
its own call instead of retrying blindly or giving up.

### Checklist

- [ ] Catalogue under ~15 tools, or the excess is justified.
- [ ] No two tools a reasonable person could confuse.
- [ ] Every description says when to use *and* when not to.
- [ ] Every parameter has a schema with types and required fields.
- [ ] Errors are actionable and name the offending parameter.
- [ ] Each tool declares `permission` and `side_effect` (security S2/S3).

---

## Runtime context management

Distinct from the *developer* context files (`references/context-and-cost.md`).
This is about the agent's own conversation at runtime.

Context is finite with diminishing marginal returns, so the goal is the smallest
set of high-signal tokens that supports the task — not the largest window you can
afford.

### Compaction

When a conversation approaches the window, summarize and reinitialize from that
summary rather than truncating. `src/<pkg>/agent/compaction.py` implements the
deterministic half; the summary itself is a model call, covered by evals.

**Tune the compaction prompt on real traces: maximize recall first** so nothing
important is dropped, **then improve precision** by cutting the superfluous. The
failure mode of aggressive compaction is losing something subtle and not noticing
for several turns.

Preserve, in priority order: decisions and their reasoning, unresolved questions,
established facts and identifiers, and stated constraints — especially things
already ruled out. Discard pleasantries and superseded intermediate reasoning.

Keep the **first** turns as well as the recent ones. The opening usually carries
the task definition, which summaries erode first.

### Sub-agents

Sub-agents are a context tool: they isolate work in a separate window so the
parent's context stays clean.

**Multi-agent systems fail through context pollution.** Sharing one context
across sub-agents costs cache efficiency and confuses each agent with irrelevant
detail. For a discrete task with clear inputs and outputs, spawn a sub-agent with
a *fresh* context and pass only the specific instruction. Share full history only
when the sub-agent genuinely needs the whole trajectory — which is rarer than it
seems.

### If you go multi-agent, read MAST first

The Multi-Agent System Failure Taxonomy (arXiv 2503.13657, NeurIPS 2025) derives
**14 failure modes** from 1600+ annotated traces across 7 frameworks, at high
inter-annotator agreement (κ = 0.88), in three categories:

1. **System design** — bad task routing, inadequate error handling, resource contention.
2. **Inter-agent misalignment** — communication breakdown, conflicting objectives.
3. **Task verification** — missing output validation, errors propagating down the chain.

Their conclusion is the same one this framework is built around: **failures stem
from poor system design, not model capability.** Better orchestration beats
bigger models. Use the 14 modes as an eval checklist for a multi-agent system,
and prefer a single agent until the task genuinely requires more.

---

## Sources
- Anthropic — *Writing effective tools for AI agents*.
- Anthropic — *Effective context engineering for AI agents* (compaction, recall-then-precision).
- MindStudio — *The Subtraction Principle: Why Removing Agent Tools Often Improves Performance*.
- OpenAI — *A practical guide to building agents*.
- Arize — *Context management in agent harnesses: memory, files, and subagents*.
- arXiv 2503.13657 — *Why Do Multi-Agent LLM Systems Fail?* (MAST).
