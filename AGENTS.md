# AGENTS.md

Instructions for any AI coding agent working **on or with** this repo — Claude,
Cursor, Gemini, Copilot, Codex, Windsurf, or a local model. Vendor-specific
files (`CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`,
`.github/copilot-instructions.md`) point here. Edit this one.

## What this repo is

`agent-builder` is a framework for building enterprise AI agents: an
orchestrator (`SKILL.md`), nine phase sub-skills plus two standalone ones
(`skills/`), reference docs (`references/`), and a project template
(`templates/`) that gets copied into the user's new repo.

## Start here

**`CAPABILITIES.md`** — every phase, what can be invoked standalone, the CLI
tools, make targets, MCP servers and companion skills. Read it before answering
"what can this do" or "how do I…".

Regenerate it after any change:

```bash
python3 tools/capabilities.py --write    # no dependencies required
python3 tools/capabilities.py --check    # exit 1 if stale
```

## If you cannot invoke skills

Claude Code loads `skills/*/SKILL.md` on request. Other agents may have no such
mechanism — that is fine, nothing here depends on it. The skills are plain
markdown: **read the file directly.**

| You want to | Read |
|-------------|------|
| know what's available | `CAPABILITIES.md` |
| run the whole pipeline | `SKILL.md`, then `skills/<phase>/SKILL.md` in order |
| do one thing (evals, observability, security) | that phase's `SKILL.md`, `targeted` entry path |
| review an existing agent | that phase's `SKILL.md`, `audit` entry path |
| know how to talk to the user during a phase | `references/interview-protocol.md` |
| change a locked default | `skills/override/SKILL.md` |
| understand *why* a rule exists | the matching `references/*-standards.md` |

## Working rules

- **Procedure goes in `SKILL.md`; rationale goes in `references/`.** Every time
  this is violated the orchestrator grows, and it loads on every invocation.
  Root `SKILL.md` should stay near ~1,000 tokens.
- **Generated files are never hand-edited.** `CAPABILITIES.md` comes from
  `tools/capabilities.py`; `templates/FUNCTIONS.md` from
  `templates/tools/functions_index.py`. If output looks wrong, fix the source —
  the front-matter description, the docstring, the Makefile help text.
- **Interview-first is a property of the framework, not a suggestion.** Any new
  or edited phase must extract its decisions by asking, and reach a consensus
  check before writing artifacts. Never add a step that drafts a document and
  asks the user to review it — see `references/interview-protocol.md`.
- **Don't duplicate across skills.** If two phases need the same explanation, it
  belongs in a reference doc with both pointing at it.
- **Tools must run under bare `python3`.** Another agent will not have this
  repo's venv. No third-party imports in `tools/`.
- **Scope**: building, evaluating and observing agents. *Not* regulatory
  compliance, data governance, per-user data authorization, or deployment — see
  `SKILL.md` § Scope. Name those as out of scope rather than half-building them.

## Verifying a change to `templates/`

The template is a real project. Copy it somewhere under `$HOME` (Colima and
Docker Desktop do not share `/tmp`), then:

```bash
uv sync --extra dev --extra dashboard --extra evals
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run python tools/context_budget.py --check
uv run python tools/functions_index.py --check
uv run pytest tests/ -q
```

All of it must pass before committing. Deterministic tests never call a model.
