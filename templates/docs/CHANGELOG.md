# Changelog

> **Discipline: APPEND-ONLY.** Never edit or delete an existing entry. When this
> file exceeds its budget (200 lines), `make context-rotate` moves the oldest
> entries to `docs/archive/CHANGELOG-<date>.md`. Nothing is destroyed — the
> archive and git history keep everything; the live file stays cheap to read.
>
> **Why this exists:** so an agent can learn what changed recently without
> running `git log` and reading diffs, which is expensive and unsummarized.

Newest entries at the top. One entry per merged change.

Format:

```markdown
## <date> — <short title>
**What:** <one or two sentences>
**Why:** <the reason, not the mechanism>
**Touches:** `path/one.py`, `path/two.py`
**Tier:** nano | standard | deep
**Evals:** <pass-rate delta, or "n/a">
**Arch impact:** none | updated ARCHITECTURE.md
```

---

## <date> — Project scaffolded
**What:** Initial project created by agent-builder: skeleton, observability with
portable JSON traces, eval harness, deterministic test suites, context files.
**Why:** Establish the environment before any agent logic, so evals and traces
exist from the first commit.
**Touches:** repo-wide
**Tier:** standard
**Evals:** n/a (no agent yet)
**Arch impact:** created ARCHITECTURE.md
