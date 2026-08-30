# Context files and token cost control

_The problem this solves: an agent that starts every session by re-deriving the
codebase burns most of a token budget on rediscovery, not on work. Reported in
practice: ~50% of a monthly allowance consumed by repeated context pulls, most of
it re-reading code the agent had already understood in a previous session._

The fix is not a bigger context window. It is a small set of files that are
**always current**, **cheap to read**, and **authoritative**, plus a rule that
the agent reads those instead of the codebase.

---

## The four files

Scaffolded by `skills/1-scaffold`, maintained by every phase after it.

| File | Discipline | Budget | Answers |
|------|-----------|--------|---------|
| `AGENTS.md` | stable | 150 lines | how to work in this repo |
| `docs/ARCHITECTURE.md` | **snapshot — overwrite** | 300 lines | what the system looks like *now* |
| `docs/CHANGELOG.md` | append-only, rotated | 200 lines | what changed recently and why |
| `docs/TODO.md` | append-only, rotated | 250 lines | what is done, next, and why the plan moved |

Budgets are enforced by `make context-budget` and in CI. They are not cosmetic:
these files are read at the start of most sessions, so their length is a
recurring cost. An over-budget context file has become the very thing it exists
to prevent.

### Why `AGENTS.md` and not `CLAUDE.md`

The framework must work with any coding agent. `AGENTS.md` is the emerging
cross-vendor convention; `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/agents.mdc`
and `.github/copilot-instructions.md` are one-line pointers to it. One source of
truth, no drift between four copies.

### Why ARCHITECTURE.md is overwritten, not appended

An append-only architecture doc forces the reader to reconstruct the current
state from a pile of history — expensive and error-prone, exactly the waste we
are eliminating. So the file holds only the present, and history lives where
history belongs: git.

`make arch-snapshot` enforces the discipline by refusing to proceed while the
file has uncommitted changes, guaranteeing each version gets its own commit.
It **commits but never pushes** — pushing is outward-facing and can fail (no
remote, protected branch, detached HEAD) or surprise the user mid-task.

`git log -p docs/ARCHITECTURE.md` is the full history.

This file is written **for machines**: compact, structural, current. It is not
the user-facing architecture diagram, and the two should not be merged — their
audiences want opposite things.

### Why append-only files still get rotated

Append-only is right for auditability: never destroy the record of what happened
or why a plan changed. But unbounded growth recreates the cost problem. Rotation
resolves the tension — entries are moved **verbatim** into `docs/archive/`, which
agents do not read by default. Nothing is edited or deleted, and git has
everything regardless. `make context-rotate`.

### Why plan supersession is recorded, never rewritten

The most expensive context to reconstruct is *why the plan changed*. An agent
that finds "use Qdrant" with no trace of the rejected pgvector approach will
eventually re-propose pgvector. So supersessions are appended and cross-linked on
both items, with the reason and the evidence.

---

## Model tier routing

Policy: `.agent/model-policy.yml`. Router: `tools/route_task.py`.

| Tier | Use for | Cost posture |
|------|---------|--------------|
| **nano** | locating code, explaining it, regenerating indexes, formatting, changelog entries, diagrams | cheapest model, minimal reasoning |
| **standard** | implementing one nano-sized task, tests, docs, routine debugging | default |
| **deep** | architecture design/review, hard bugs the cheaper tiers failed on, eval-failure triage, security review | expensive; use sparingly |

**Decompose before escalating.** Most work that feels deep-tier is one deep
decision plus several nano tasks. Spend the expensive tier on the decision, then
run the rest cheap. A task that cannot be handed to the nano tier is usually not
small enough yet — that is the signal to split it, not to escalate.

**Floors** override keyword matching: touching `docs/ARCHITECTURE.md` is always
deep regardless of how trivial the edit sounds, because changing the
architecture description is a design act. Touching `evals/**` is at least
standard, because a wrong eval case is worse than no eval case.

### What is actually enforceable

Be honest about this — nothing in a repo can force another vendor's tool to
switch models.

| Surface | Enforcement |
|---------|-------------|
| `tools/route_task.py` | real — any human, script, or CI step gets a deterministic tier |
| `.claude/hooks/model-guard.sh` | real for Claude Code — classifies each prompt and injects the tier automatically |
| `AGENTS.md` | advisory — the agent reads and complies |
| Other tools' rule files | advisory — they point at `AGENTS.md` |

Keep hook logic in a testable module (`tools/hook_advice.py`), not inline in a
shell string. The first version of that hook lived inline, raised a
`SyntaxError` on every prompt, and failed silently because stderr was
discarded — a hook that fails quietly is worse than no hook.

---

## Session-start ritual

This is the mechanism that produces the saving. `AGENTS.md` instructs every
agent to:

1. Read `AGENTS.md`, `ARCHITECTURE.md`, the tails of `TODO.md` and `CHANGELOG.md`.
2. Run `fn_search` to locate the functions in play.
3. Read **only** those functions.

And explicitly not to: read source before `fn_search`, re-derive the
architecture from code, or run `git log`/`diff` to learn recent history.

If an agent finds itself reconstructing context one of these files should have
held, the correct fix is to improve that file — not to read more source. That
feedback loop is what keeps the system cheap over time.
