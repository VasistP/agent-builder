# Interview protocol

The default interaction style for every phase of `agent-builder`. It is
**mandatory** unless the user has recorded an `interaction.interview_mode`
override (Tier B — see `override-registry.md`).

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

> Do not write a spec, plan, design, eval set, threat model, or backlog document
> and then ask the user to review it. Ask the questions first, one small batch at
> a time, reach explicit agreement, and only then write the file.

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

**How this runs:** interview style. I'll ask you questions in small batches and
read back what I understood before writing anything. Expect to be asked, not
handed a document to skim.

**Defaults already set for you** (all locked):
- Evals + observability are built in, always — with a CI gate and portable JSON traces
- Deterministic tests never fake a model call; model behavior is measured by evals only
- Eval judge runs locally (Ollama) — a hosted judge costs money and needs your say-so
- A human checkpoint between every phase; nothing chains without your `approved`
- Security + adversarial phases are mandatory for any agent with data + tools

**What you can change** — anything, via `skills/override` (nothing else can):
- Tier C, easy: framework/stack, judge model, observability tool, thresholds, budgets, MCP set
- Tier B, deliberate: skipping/reordering phases, repo layout, **this interview style**
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

## Where an interview is required

Every phase has at least one point where information can only come from a human.
These are the mandatory interview gates:

| Phase | Interview gate |
|-------|----------------|
| 0 — discovery | the whole phase; nothing is written before consensus |
| 1 — scaffold | stack, package name, integrations to enable |
| 2 — observability | tool choice, content capture (PII), retention |
| 3 — evalset | every case's ground truth and pass bar — co-authored, never invented alone |
| 4 — testing | which deterministic units matter, what "correct" means for each |
| 5 — agent skeleton | the one end-to-end path to prove, and its success criterion |
| 6 — feature | the feature's acceptance criteria and eval delta expectation, before any code |
| 7 — security | trifecta verdict, which tools are side-effecting, who approves what |
| 8 — adversarial | attacker model, what counts as a breach here, accepted risks |

In `audit` mode the interview is shorter but not skipped: confirm scope, what
they already believe is weak, and what a finding needs to look like to be
actionable for them.

## Turning the interview off

Some users — repeat users, batch runs, CI-driven scaffolds — genuinely want the
document-first flow. That is a legitimate choice, and it is a **Tier B
override**:

```
override interaction.interview_mode
```

`skills/override` will assess it, warn about what gets lost, and record it.
Document-first mode still requires the phase checkpoints; it drops only the
question-by-question extraction and the consensus check, replacing them with a
written proposal the user is explicitly asked to read closely.

Never turn it off because the user seems impatient, gives short answers, or says
"just do it". That is a signal to ask fewer and better questions, not to stop
asking. Only an explicit override counts.
