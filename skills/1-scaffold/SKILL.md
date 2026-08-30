---
name: agent-builder-1-scaffold
description: >-
  Phase 1 of agent-builder. Create the project skeleton, dev tooling, docstring
  enforcement, the FUNCTIONS.md index + fn_search CLI, and .mcp.json. Use after
  the discovery spec is approved.
---

# Phase 1 — Scaffold

Goal: a runnable, empty project skeleton with all tooling and guardrails in
place. No agent logic yet.

## Prerequisites / standalone notes

- Needs `.agentbuilder/spec.md` (phase 0). If missing, run discovery first or ask
  the user for the stack + package name directly.
- If run inside an existing project (`targeted` mode), do **not** overwrite files.
  Instead: detect what's already there, and only add the missing pieces
  (docstring config, `tools/fn_search.py`, `FUNCTIONS.md`, `.mcp.json`, Makefile
  targets). Report what was skipped.

**Locked.** Repo layout, docstring enforcement, and the index drift check are
framework defaults — see `references/override-registry.md`. Stack choice is the
one thing you actively ask about here (Tier C), but changing it *after* scaffold
goes through `skills/override`.

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

### 6. MCP config
Copy `templates/.mcp.json` — context7, playwright, memory, sequential-thinking,
**version-pinned**, each with a vetting date.

**Every server must pass the vetting checklist in `references/mcp-catalogue.md`
before it is added; adding an unvetted one is a Tier B override.** Explain why to
the user: 66% of scanned MCP servers have security findings, and tool poisoning —
malicious instructions in a tool's description, which the model reads and the
human never sees — is the leading attack on enterprise agents. Never use a bare
`npx -y pkg`; that installs unreviewed code on every launch.

**Database MCP is conditional.** Do not preinstall one. Once the spec names
concrete stores, add a *single* matching server with a **read-only role**. A
general-purpose database MCP holding write credentials is the largest
excess-agency risk available. If nothing fits the user's internal systems,
recommend the `mcp-builder` skill to build a narrow one they control.

### 7. Verify
Run `make setup` then `make test`. The skeleton ships one trivial passing
deterministic test so the harness is proven green.

## Checkpoint

Checkpoint block. Verify commands: `make setup && make test && make lint && make
functions-index`. User replies `approved`.
