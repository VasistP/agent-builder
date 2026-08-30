# AGENTS.md

Canonical instructions for any AI coding agent working in this repo — Claude,
Gemini, Copilot, Cursor, Codex, or a local model. Vendor-specific files
(`CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md`)
are pointers to this file. Edit this one.

**Keep this file under 150 lines.** It is read at the start of every session, so
its length is a recurring cost. `make context-budget` enforces the limit.

---

## Read these first, in this order. Stop as soon as you have enough.

| # | File | Gives you |
|---|------|-----------|
| 1 | this file | how to work here |
| 2 | `docs/ARCHITECTURE.md` | current system shape — authoritative and current by construction |
| 3 | `docs/TODO.md` (tail only) | what is done, what is in flight, what changed in the plan |
| 4 | `docs/CHANGELOG.md` (tail only) | what changed recently and why |
| 5 | `FUNCTIONS.md` or `tools/fn_search.py` | **only** the functions you need to touch |

## Do not do these — they are how token budgets get burned

- **Do not read source files before `fn_search` tells you which ones.**
  Run `python tools/fn_search.py "<what you want to change>"` first. It returns
  `path:line — signature — summary` for the handful of functions that matter.
- **Do not re-derive the architecture by reading the codebase.**
  `docs/ARCHITECTURE.md` is a current-state snapshot, not a historical log. Trust
  it. If it is wrong, fix it — that is a bug.
- **Do not run `git log` / `git diff` to learn what changed recently.**
  `docs/CHANGELOG.md` has it, already summarized.
- **Do not re-read a file you just wrote** to confirm the write succeeded.
- **Do not pull whole directories into context "for background".**

If you find yourself reconstructing context that one of these files should have
held, the fix is to improve that file — not to read more source.

---

## Model tiers — use the cheapest tier that can do the job

Policy lives in `.agent/model-policy.yml`. Ask the router when unsure:

```bash
python tools/route_task.py "regenerate the function index"   # -> nano
python tools/route_task.py "redesign the retrieval layer"    # -> deep
```

| Tier | Use for | Never use for |
|------|---------|---------------|
| **nano** | locating code, reading a function, regenerating the index, formatting, lint autofix, writing a changelog entry, summarizing a diff, explaining existing code to a human | anything requiring a design decision |
| **standard** | implementing one nano-sized task, writing tests, updating docs, routine debugging | architecture changes |
| **deep** | architecture design or review, hard bugs the standard tier already failed on, eval-failure triage, security review | anything the cheaper tiers can do |

**Decompose before you escalate.** Most work that feels like it needs the deep
tier is really one deep decision plus several nano tasks. Split it, spend the
expensive tier only on the decision, and run the rest cheap. A task that cannot
be handed to the nano tier is usually not yet small enough.

---

## Required bookkeeping — every change, no exceptions

These three files are what make the next session cheap. Updating them is part of
the change, not an optional extra.

### `docs/CHANGELOG.md` — append-only
Add an entry for every merged change: what changed, why, which model tier did it.
Never edit or delete past entries. When the file exceeds its budget,
`make context-rotate` moves the oldest entries to `docs/archive/`.

### `docs/TODO.md` — append-only, including plan changes
Append what you completed and what is next. **When the plan changes, append the
supersession — never rewrite the old entry:**

```markdown
- [x] 12. Add pgvector retrieval adapter
- [~] 13. SUPERSEDES 12 — switching to Qdrant; pgvector recall was inadequate
         on the 2026-08 eval slice. See CHANGELOG 2026-08-29.
```

The history of *why the plan moved* is the most expensive thing to reconstruct.

### `docs/ARCHITECTURE.md` — snapshot, NOT append-only
This is the one file that gets overwritten. It must always describe the system as
it is **now**, so an agent can read it once and stop.

Before changing it:

```bash
make arch-snapshot     # verifies the current version is committed, so the old
                       # state is preserved in git history and not in the file
```

Then overwrite or edit freely. History lives in `git log -p docs/ARCHITECTURE.md`.
Do not append change history into this file — that is what CHANGELOG is for.

This is **not** the user-facing architecture diagram. It is written for machine
reading: compact, structural, current.

---

## Working rules

- Google-style docstrings on every function — they power `FUNCTIONS.md` and
  `fn_search`, which is how the next agent avoids reading your code.
- Run `make functions-index` after changing any function; CI fails on drift.
- Deterministic code is test-first. Model behavior is covered by evals, never by
  faked model calls. See `docs/` and the framework's `references/methodology.md`.
- Nothing merges without both a deterministic test and an eval case.
- Framework defaults are locked; changing one requires the override skill.

## Commands

```bash
make setup             # install deps + hooks
make test              # deterministic suites, zero tokens
make lint              # ruff + mypy + docstring rules
make eval              # eval suite (local judge by default)
make obs-up            # observability dashboard
make functions-index   # regenerate FUNCTIONS.md
make context-budget    # check context files are within budget
make context-rotate    # archive old CHANGELOG/TODO entries
make arch-snapshot     # guard before rewriting ARCHITECTURE.md
```
