# Interview protocol

The interaction style for the phases whose inputs exist only in the user's head:
**0 (discovery), 3 (evalset), 6 (feature), 7 (security), 8 (adversarial)**. In
those five it is **mandatory**, and only a completed run of `skills/override` can
lift it (Tier B — see `override-registry.md`).

Phases **1, 2, 4 and 5** run in `propose` mode instead: the framework has a
defensible default there, so state it, get an explicit yes, and build. Those
phases don't need the ceremony — handing someone a blank where a sane default
exists wastes the attention you need for the questions that matter.

## Why this exists

The failure mode this prevents is specific and common: the agent writes a
plausible markdown document, asks "does this look right?", and the user skims it
and says yes. Nothing was actually decided. Every nuance the document guessed at
is now silently locked in, and the first time anyone notices is three phases
later when the evals encode the wrong ground truth.

**People do not read markdown in detail.** They *do* answer a direct question.
So the framework extracts decisions through conversation and writes the document
*afterwards*, as a record of what was agreed — never as a substitute for
agreeing.

## The rule

> In an interview-locked phase, do not write a spec, plan, design, eval set,
> threat model, or backlog document and then ask the user to review it. Ask the
> questions first, one small batch at a time, reach explicit agreement, and only
> then write the file.

A document produced before the interview is a **proposal the user must approve**,
which is exactly the dynamic that lets nuance slip. A document produced after the
interview is a **transcript of decisions already made**, which is the one that
holds up.

## How to run an interview

### 1. Batch small, never dump

2–4 questions per turn. Never present the full question list — it reads as a form
and gets answered like one. Ask, listen, and let the answers reshape what you ask
next.

### 2. One decision at a time, and make it concrete

Bad: "What are your data sources and constraints?"
Good: "You said it reads from Snowflake. Which tables — and does any of them
carry customer PII?"

Every question should be answerable in a sentence or two by someone who knows
their own system. If a question requires the user to design something on the
spot, you are asking the wrong question — offer 2–3 concrete options and let them
choose.

### 3. Push back on vague answers

"Fast", "secure", "the usual", "standard stuff", "you decide" are not answers.
Ask for the number, the example, the table name, the actual failure they are
worried about. One follow-up is normal; if the user genuinely does not know, say
you will record it as an open assumption and move on — do not silently invent a
value.

### 4. Offer options rather than open prompts on technical choices

Where the framework already has an opinion (judge model, observability tool,
framework), present the default plus the realistic alternatives and the trade-off
in one line each. The user picks. Do not make them guess what the menu is.

### 5. Read back before writing anything

Close every interview with a **consensus check** — a compact, spoken-language
summary of what you understood, including the things you inferred rather than
were told:

```
### Consensus check — <phase>
Here's what I understood. Correct anything that's wrong.

1. <decision> — <the specific value agreed>
2. ...

Assumptions I made where you didn't specify:
- <assumption> — <what I'll do unless you say otherwise>

Still open:
- <question> — <why it matters / who can answer it>

Say `agreed` and I'll write this up, or tell me what to change.
```

Wait for it. Do not write the artifact until the user responds. If they correct
something, re-issue the corrected line — not the whole block.

### 6. Then write the file, then checkpoint

The artifact (`spec.md`, an eval set, a threat model) is written *after*
`agreed`. The phase checkpoint that follows is a second, different gate: consensus
check = "did I understand you", checkpoint = "is the work you can now see
acceptable". Both are required. Do not merge them.

## Session opener

Print this before phase 0, or before any standalone or targeted run, so the user
knows the interaction style they are opting into and what they are allowed to
change. Adapt the wording; keep every section. Skip it only when `.agentbuilder/`
already exists — then summarize the current mode and any active overrides
instead.

```
### Good to know before we start

**How this runs:** interview style for the parts only you can answer — discovery,
eval cases, each feature's acceptance criteria, security and red-teaming. I'll
ask in small batches and read back what I understood before writing anything.
For scaffolding, observability, tests and the first skeleton I'll propose sane
defaults and just get a yes from you.

**Defaults already set for you** (all locked):
- Evals + observability are built in, always — with a CI gate and portable JSON traces
- Deterministic tests never fake a model call; model behavior is measured by evals only
- Eval judge runs locally (Ollama) — a hosted judge costs money and needs your say-so
- A human checkpoint between every phase; nothing chains without your `approved`
- Security + adversarial phases are mandatory for any agent with data + tools

**What you can change** — anything, via `skills/override` (nothing else can):
- Tier C, easy: framework/stack, judge model, observability tool, thresholds, budgets, MCP set
- Tier B, deliberate: skipping/reordering phases, repo layout, **unlocking the interview on a given phase**
- Tier A, hard: turning off evals, observability, trace export, the CI gate, or the checkpoints

I'll assess any override against *this* repo, tell you what it costs, offer a
narrower alternative, and record it in `.agentbuilder/overrides.md`.

**Out of scope here:** regulatory compliance, data governance, per-user data
authorization, deployment and secrets. I'll name them if they come up, not
half-build them.

Ready? First question:
```

## What the interview is not

- **Not** a questionnaire dumped in one message.
- **Not** a document plus "let me know if you'd like changes."
- **Not** a single confirmation at the end of a phase.
- **Not** an excuse to ask about things the repo can tell you. Read the code, the
  spec, and `.agentbuilder/` first; ask only what you genuinely cannot determine.
  Asking a user something you could have looked up burns the goodwill you need
  for the questions that matter.

## Which phases interview, and which propose

The test is simple: **can the framework supply a defensible starting point?** If
yes, propose one. If the answer exists only in the user's head, ask — because a
guess there becomes the ground truth every later phase is measured against.

### Interview-locked (mandatory)

| Phase | What only the user can answer |
|-------|-------------------------------|
| 0 — discovery | the whole phase: purpose, scope, data, constraints, success bars. Nothing is written before consensus |
| 3 — evalset | every case's ground truth and pass bar — co-authored, never invented alone and shown for approval |
| 6 — feature | the feature's acceptance criteria and the eval delta expected, before any code |
| 7 — security | trifecta verdict, which tools are genuinely side-effecting, who approves what |
| 8 — adversarial | the attacker model, what counts as a breach *here*, which risks are accepted |

### Propose mode

| Phase | Default to state, then confirm |
|-------|-------------------------------|
| 1 — scaffold | Python 3.12 + LangGraph, package name from the spec; ask which catalogued integrations to enable |
| 2 — observability | tool by agent type, content capture off, retention unbounded; confirm anything the spec doesn't settle — content capture is a PII decision, so never flip it silently |
| 4 — testing | the deterministic units you'll cover and what each asserts; confirm anything you had to guess |
| 5 — agent skeleton | the one end-to-end path you'll prove and its success criterion |

Propose mode is not a licence for silent decisions. State what you are about to
do, get a yes, then build. The phase checkpoint still applies.

In `audit` mode, all phases interview briefly: confirm scope, what they already
believe is weak, and what a finding must look like to be actionable for them.

## Turning the interview off

An interview-locked phase can be unlocked — for **one phase or all five** — but
only by **running `skills/override`** and completing its protocol. Nothing else
counts:

- typing the word "override" at a phase skill does **not** work; that skill has
  no authority to change this and must refuse and point here
- "skip the questions", "just generate it", "I don't have time", terse answers,
  or visible impatience are **not** overrides — they mean ask fewer and better
  questions
- a previous override of a *different* phase does not carry over; scope is
  per-phase and recorded that way

When the user genuinely wants this, say:

> That's a locked default. Run `skills/override` and I'll assess what dropping
> the interview costs in this repo, show you the narrower options, and record it.

`skills/override` will assess it, warn about what gets lost, require the Tier B
confirmation, and log the scope in `.agentbuilder/overrides.md` — e.g.
`interaction.interview_mode = propose (phase 3)`, not a blanket flag.

Unlocked phases fall back to `propose` mode, not to silence: a written proposal
the user is explicitly asked to read closely, plus the phase checkpoint, which is
never waivable here.

The legitimate case is a run with **no human present** — CI, batch scaffolding, a
headless agent. An interview with nobody to answer it is just a stall. Say so and
approve it after the protocol.
