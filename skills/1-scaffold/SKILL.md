---
name: agent-builder-1-scaffold
description: >-
  Phase 1 of agent-builder. Create the project skeleton, dev tooling, docstring
  enforcement, the FUNCTIONS.md index and fn_search CLI, the agent context files,
  and the on-demand integration catalogue. Use after the discovery spec is
  approved.
---

# Phase 1 — Scaffold

Goal: a runnable, empty project skeleton with all tooling and guardrails in
place. No agent logic yet.

**Propose, don't interrogate.** This phase has defensible defaults, so state the
stack and package name up front, get an explicit yes on which catalogued
integrations to enable, then build. No consensus-check ceremony — but no silent
decisions either, and the phase checkpoint still applies. →
`references/interview-protocol.md`

## Prerequisites / standalone notes

- Needs `.agentbuilder/spec.md` (phase 0). If missing, run discovery first or ask
  the user for the stack + package name directly.
- If run inside an existing project (`targeted` mode), do **not** overwrite files.
  Instead: detect what's already there, and only add the missing pieces
  (docstring config, `tools/fn_search.py`, `FUNCTIONS.md`, `.mcp.json`, Makefile
  targets). Report what was skipped.

**Locked** — defaults here can only change via `skills/override`; refuse and point there. Stack choice is the one thing you actively ask about here.

## Steps

### 1. Confirm the stack
- Recommend **Python 3.12 + LangGraph**. Explain why (state/checkpointing, broad
  ecosystem, good tracing hooks).
- Offer alternatives from `references/stack-options.md` and ask if the company
  mandates one. Whatever the user picks, adapt the skeleton; the rest of the
  pipeline is framework-agnostic.

### 2. Copy the skeleton
From `templates/` (this skill's sibling), copy into the project root:
- `pyproject.toml` — uv, ruff (incl. `D` pydocstyle rules, Google convention),
  mypy, pytest.
- `Makefile` — `setup`, `test`, `test-unit`, `test-regression`, `test-integration`,
  `eval`, `obs-up`, `obs-down`, `functions-index`, `lint`.
- `src/<pkg>/` with `agent/ tools/ data/ observability/ evals/` packages, each
  with an `__init__.py` and a module-level docstring.
- `tools/functions_index.py`, `tools/fn_search.py`.
- `tests/{unit,regression,integration}/` with `conftest.py`.
- `.github/workflows/ci.yml`, `ci/eval.yml`.
- `.env.example`, `.gitignore`, `README.md`.

Rename `<pkg>` to the spec's package name.

### 3. Docstring guardrail
- Ruff `D` rules on, `pydocstyle` convention = google, enforced in `make lint`
  and CI.
- Every function/method/module must have a Google-style docstring. See
  `references/deterministic-testing.md` and root `SKILL.md` for why (cheap
  targeted search).

### 4. Function index + search
- `make functions-index` runs `tools/functions_index.py`: AST-walk `src/`, emit
  `FUNCTIONS.md` (path · signature · one-line summary from the docstring).
- CI runs it and fails if `FUNCTIONS.md` is out of date (drift check).
- `tools/fn_search.py "<query>"` does a ranked AST/docstring search and prints
  `path:line — signature — summary`. Document it in the project README as step 1
  for any change.

### 5. Agent context files (mandatory)
Copy and fill in, per `references/context-and-cost.md`:
- `AGENTS.md` — canonical, vendor-neutral. Fill in project specifics; keep it
  under 150 lines.
- `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/agents.mdc`,
  `.github/copilot-instructions.md` — one-line pointers. Never duplicate content.
- `docs/ARCHITECTURE.md` — snapshot template; fill from the spec.
- `docs/CHANGELOG.md`, `docs/TODO.md` — seeded, append-only.
- `.agent/model-policy.yml` — set the provider(s) actually in use.
- `.claude/hooks/model-guard.sh` + `.claude/settings.json` — Claude Code routing
  hook. Tell the user it is advisory-by-injection, and that other tools read the
  same policy via `tools/route_task.py`.

Verify: `make context-budget` passes and `make route T="find the parser"`
returns `nano`.

### 6. External integrations — on demand, never bundled
The scaffold ships **no `.mcp.json`**. It ships a catalogue
(`.agent/integrations.yml`) and a checker.

1. Run `make integrations`. It reports which MCP servers are configured, which
   skills are discoverable, and what each would unlock.
2. Show the user the list and **ask which they want**. Enable only those:
   `make integrations-enable NAME=context7`. Each write is version-pinned with
   its vetting line.
3. Recommend `context7` for most projects; `playwright` only if there is a UI or
   the agent browses; `memory` only if the build spans sessions.
4. Anything not in the catalogue is unvetted — adding it is a Tier B override.
   → `references/mcp-catalogue.md`
5. **No database MCP here.** Add one only after discovery names stores, with a
   read-only role, or build a narrow one with `mcp-builder`.

Skills are used *if available*. Built-ins aren't visible on disk, so check your
own skill listing rather than trusting the checker's `?`. When one is missing,
use the fallback in `.agent/integrations.yml` — never skip the step.

### 7. Verify
Run `make setup` then `make test`. The skeleton ships one trivial passing
deterministic test so the harness is proven green.

## Checkpoint

Checkpoint block. Verify commands: `make setup && make test && make lint && make
functions-index`. User replies `approved`.
