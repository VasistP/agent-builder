---
name: agent-builder-override
description: >-
  The ONLY way to change any default, structure, or configuration defined by
  agent-builder — including the evals and observability non-negotiables. Use
  when the user wants to skip, disable, replace, or reconfigure anything the
  framework enforces. Assesses the specific repo, warns about disadvantages,
  offers narrower alternatives, and records every override in a ledger.
---

# agent-builder-override

Every default in this framework is locked. No other skill may change one. When a
user asks a phase skill to skip evals, drop the trace export, swap the judge, or
restructure the repo, that skill **refuses and points here**.

The friction is the point: invoking this skill is a deliberate pause to decide
whether you actually want the override.

## Hard rules

1. **Never override anything without running the full protocol below.** Not even
   a "small" config change.
2. **Never approve an override on the user's behalf**, and never infer consent
   from the fact that they invoked this skill. Invoking it means "assess this",
   not "do this".
3. **Always assess against the actual repo**, not in the abstract. A given
   override can be reasonable in one codebase and reckless in another. Say which
   this is.
4. **Always offer a narrower alternative** that gets them most of what they want
   at lower cost. Most override requests have one.
5. **Always record the outcome** in `.agentbuilder/overrides.md`, including
   declined requests — the reasoning is worth keeping.

## Protocol

### Step 1 — Identify the item and its tier

Look it up in `references/override-registry.md`. Every overridable item has a
tier, a default, a blast radius, and a revert path. If the request doesn't map to
a registry entry, treat it as **Tier B** and add a registry entry as part of the
override.

| Tier | Covers | Ceremony |
|------|--------|----------|
| **A — Protected** | the non-negotiables: evals, observability, portable trace export, eval CI gate, phase checkpoints | full protocol + typed confirmation phrase + expiry required by default |
| **B — Structural** | phase order/skipping, repo layout, docstring enforcement, index drift check, no-model-call guard, the deterministic-testing rule | full protocol + explicit `override` confirmation |
| **C — Configuration** | stack/framework, judge provider+model, observability tool, data stores, thresholds, budgets, case counts, MCP set, dashboard panels | short protocol (assessment + one confirmation), no expiry needed |

### Step 2 — Assess *this* repo

Gather signals before saying anything about advantage or disadvantage:

- `.agentbuilder/spec.md` → agent type, compliance constraints, success criteria,
  feared failure modes.
- `src/**/tools/` → how many tools; is tool selection non-trivial?
- `evals/*.jsonl` → how many cases; are they passing; do they cover the thing
  being overridden?
- `logs/traces/` → is there real traffic; are traces actually being read?
- `evals/results/` → has the eval suite ever caught a regression? (If yes, that
  is the strongest possible argument against weakening it.)
- CI config → is the gate live; does anything else catch this class of bug?
- `.agentbuilder/overrides.md` → are they stacking overrides? Three small ones
  can add up to "no safety net", and that compounding must be called out.

Then produce a verdict using the heuristics in
`references/override-registry.md` § *Assessment heuristics*. Be specific and
quantitative where you can — "your 214-case suite would cost roughly $6 per CI
run at Haiku rates, ~$180/month at your current PR volume" beats "this may be
expensive".

### Step 3 — Present the decision

Output exactly this block. Do not soften a disadvantage, and do not manufacture a
disadvantage that doesn't apply to their repo.

```
### Override request: <item>  (Tier <A|B|C>)
Current default: <value + where it's enforced>
Requested change: <value>

**Assessment for THIS repo**
<2-5 bullets citing concrete signals you actually found: agent type, tool count,
eval coverage, trace volume, prior caught regressions, compliance constraints>

Verdict: ADVANTAGE | NEUTRAL | DISADVANTAGE | STRONG DISADVANTAGE

**What you lose**
- <specific, concrete consequences — the failure that becomes invisible>

**What you gain**
- <state it honestly; if the gain is small, say so>

**Narrower alternative I'd recommend instead**
<a partial override that keeps most of the safety>

Scope: one-time | time-boxed (expires <date>) | permanent
Revert: <exact command / edit to undo this>
```

Then ask for confirmation:

- **Tier A** — require the user to type: `override <item> — I accept <the single
  worst consequence>`. Nothing else counts as consent. Default to proposing a
  time-boxed override with an expiry date; permanent Tier A overrides need a
  second explicit confirmation.
- **Tier B** — require the word `override`.
- **Tier C** — a plain yes is fine.

If the verdict is **STRONG DISADVANTAGE**, say so plainly before the
confirmation prompt and state that you recommend against it. Then still let them
decide — this skill informs, it does not veto.

### Step 4 — Apply and record

1. Make the change.
2. Append to `.agentbuilder/overrides.md` (create from the template if absent):

```
| Date | Item | Tier | From → To | Scope/Expiry | Verdict | Accepted consequence | Revert |
```

3. If Tier A or B, add a comment at the code/config site pointing to the ledger
   row, so the next reader knows it was deliberate:
   `# OVERRIDE: evals CI gate disabled — see .agentbuilder/overrides.md 2026-08-29`
4. If time-boxed, note the expiry in the ledger and remind the user at the next
   checkpoint after it lapses.

## Reverting

`revert <item>` restores the default, removes the ledger row's active status
(keep the history — mark it `reverted`), and re-enables any enforcement the
override disabled. Always offer this when an expiry lapses.

## Declining requests

If the user changes their mind, record the declined request in the ledger too,
with the assessment. It saves re-litigating the same decision in three months.
