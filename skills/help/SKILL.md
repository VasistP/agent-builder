---
name: agent-builder-help
description: >-
  Tell the user exactly what to do next on their agent-builder project, based on
  what they have already built and what is still ahead. Use whenever someone is
  stuck, asks "what next", "where am I", "what should I do now", "I don't know
  what to do", or wants to resume a project after a break. Reads the project's
  real state — spec, progress, eval sets, traces, tests, TODO — and returns ONE
  recommended next action with copy-pasteable steps, never a menu of options.
---

# agent-builder help — what do I do next?

The framework's phase list says what the steps *are*. This answers what **your**
next step is, from what is actually on disk.

**Give one answer.** A user who asks "what should I do next?" and receives three
options, a summary of the pipeline, or "it depends on your priorities" is worse
off than before they asked — that is the failure this skill exists to fix. Pick
the single best next action, say why it and not something else, and make it
followable without further decisions. If two things are genuinely tied, pick the
one that unblocks the most and say so in one clause.

## Step 1 — Read the actual state

```bash
python3 <agent-builder>/tools/next_step.py --project .
```

It reports every phase as done / partial / todo with the evidence behind each
call, any blockers, and the earliest incomplete gate. Rules it follows, which you
must not contradict:

- **Artifacts on disk are the evidence.** No bookkeeping file is required and
  none is prescribed. If `.agentbuilder/progress.md` happens to exist it is read
  as a bonus signal about approvals, in whatever shape its author chose — do not
  ask the user to adopt a format, create the file, or keep it current.
- **Unclear evidence reports unknown**, not done. Telling someone to leave a
  phase they have not finished is the expensive wrong answer.
- **Approval unknown ≠ unapproved.** With no progress file, judge by artifacts
  and say so, rather than flagging finished phases as unapproved.

Combine that with what you already know: this conversation, the phase list below,
and whatever the project writes as it goes — `docs/TODO.md`, `docs/CHANGELOG.md`,
recent commits. Read only what the target phase needs: `.agentbuilder/spec.md`
for the backlog and constraints, `.agentbuilder/overrides.md` if present (a
disabled guarantee changes what "done" means), and that phase's
`skills/<n>-<name>/SKILL.md`.

## Step 2 — Pick the next action

In priority order — the first that applies wins:

1. **A blocker.** No `.env`, judge unreachable, coverage gate failing, a lapsed
   time-boxed override. Clearing it *is* the next step; everything else is
   blocked behind it.
2. **A phase built but recorded as unapproved.** Only when a progress file
   actually says so. The step is the checkpoint: show what was built, the verify
   commands, and ask for `approved`.
3. **The earliest partial phase.** Finish it. Be quantitative — "write 12 more
   single-response cases", not "continue the eval set".
4. **The earliest todo phase.** Start it.
5. **Everything done.** Next backlog feature via `6-feature`, or re-run phase 8
   if tools or prompts changed since the last red-team.

## Step 3 — Answer in this shape

```
### Where you are
<2–4 lines: phases done, and the one you're in the middle of>

### Do this next
<one sentence, imperative>

Why this and not something else: <one sentence>

#### Steps
1. <exact command, or the exact words to type at the agent>
2. ...
3. ...

Done when: <an observable check, with the command that shows it>

### After that
1. <next step, one line>
2. <the one after, one line>
```

Rules for the steps:

- **Copy-pasteable.** A shell command, or the literal prompt to type — not "ask
  the agent to set up evals".
- **Each step is one action** with a visible result. If a step needs a decision,
  the decision is its own step with your recommendation stated.
- **Name files and numbers**: `evals/single_response.jsonl`, "12 more cases",
  `make eval-coverage`.
- **Ground every claim in the report.** Never assert a phase is done without the
  evidence line that says so.
- **Say when the next step is conversational.** Some steps are "run
  `skills/3-evalset` and answer its questions" — say that plainly, and warn that
  phases 0, 3, 6, 7 and 8 will interview them and need their attention.

## Step 4 — If they are stuck *inside* a phase

"What next" often means "this phase is not working". Diagnose before advising:
read the last error, check `make eval-coverage`, `make tools-posture`,
`logs/traces/` for a recent span, and `evals/results/` for the last run. Then fix
the specific thing. Do not restart the phase — that discards work and rarely
addresses the cause.

## Never

- Present a menu, or end with "let me know which you'd prefer".
- Recommend skipping a phase. That is `skills/override`, and only the user
  invokes it.
- Invent state. If the report says unknown, ask **one** question to resolve it.
