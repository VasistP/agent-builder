---
name: agent-builder-capabilities
description: >-
  Show everything agent-builder can do — every phase, which ones can be called
  standalone or pointed at an existing codebase, the CLI tools and make targets
  in a scaffolded project, catalogued MCP servers, companion skills, and the
  reference docs. Use when someone asks what agent-builder offers, what they can
  invoke, how to use a specific part, or what a command does.
---

# agent-builder capabilities

Answers "what can this do, and what can I invoke?" Run the generator — it reads
live repo state, so it cannot drift:

```bash
python tools/capabilities.py
```

`CAPABILITIES.md` holds the same content for anyone browsing on GitHub;
`--write` refreshes it, `--check` fails if it is stale.

## How to answer

**Do not paste the whole index.** It is a lookup table, not an answer. Read it,
then respond to what was actually asked:

- *"What can agent-builder do?"* — the four invocation modes and the phase list,
  nothing more.
- *"I already have an agent, can I use this?"* — yes: name the phases with an
  `audit` or `add` entry path and what each would tell them.
- *"What does `make route` do?"* — that one target, plus why it exists.
- *"How do I add an MCP server?"* — the on-demand flow and the vetting gate.

Lead with what is relevant to their situation. If they have an existing
codebase, the `audit` and `targeted` modes matter far more than the greenfield
pipeline.

## The things people most often don't realize

Surface these when relevant — they are the difference between using one phase
and using the framework:

- **Every phase with an `audit` path works on a codebase this framework never
  built.** "Review our eval setup" and "red-team our agent" are valid entry
  points on day one.
- **`targeted` mode exists.** You do not have to run the whole pipeline to get
  observability or evals.
- **`override` is the only way to change a default** — and it assesses the
  request against *your* repo rather than answering in the abstract.
- **Nothing external is bundled.** MCP servers and companion skills are
  catalogued and installed on demand; `make integrations` shows what each unlocks.
- **The project tools are for the agent as much as the human.** `fn_search`
  before reading source, and `route_task` before spending a big model on
  mechanical work, are the two habits that most reduce token spend.

## Keeping it honest

The index is generated from front-matter, docstrings, Makefile help text and
`.agent/integrations.yml`. If an entry reads wrong, the **source** is wrong —
fix the description where it lives, then regenerate. Never edit
`CAPABILITIES.md` directly.

Run `python tools/capabilities.py --write` after adding a phase, reference doc,
tool or make target.
