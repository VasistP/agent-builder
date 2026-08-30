# Architecture — current state

> **Discipline: SNAPSHOT, not a log.** This file describes the system as it is
> *right now*. Overwrite it when the architecture changes; never append change
> history here (that is `CHANGELOG.md`). Run `make arch-snapshot` first so the
> previous version is preserved as its own git commit.
>
> **Audience: machines.** Written to be read once, cheaply, by an AI agent
> orienting itself. Compact and structural. This is *not* the user-facing
> architecture diagram.
>
> **Budget: 300 lines.** Enforced by `make context-budget`. If you are over,
> you are describing implementation detail that belongs in docstrings.

_Last updated: <date> · Reflects commit: <sha>_

## What this system does

<2-3 sentences. The agent's purpose, from .agentbuilder/spec.md.>

## Shape

```
<ASCII block diagram: entrypoint -> graph nodes -> tools -> data sources,
 plus the observability and eval side-channels. Keep it under ~20 lines.>
```

## Components

| Component | Path | Responsibility | Talks to |
|-----------|------|----------------|----------|
| Entrypoint | `src/<pkg>/agent/run.py` | `run_once` / `chat`; stable public contract the eval runner calls | graph |
| Graph | `src/<pkg>/agent/graph.py` | orchestration; step budget | model shim, tools |
| Model shim | `src/<pkg>/agent/model.py` | the only place a model is called; emits the LLM span | provider API |
| Tool registry | `src/<pkg>/tools/registry.py` | registration, schema, dispatch | tools |
| Data adapters | `src/<pkg>/data/` | one adapter per source, implements `Store` | external stores |
| Observability | `src/<pkg>/observability/` | OTel GenAI spans + portable JSON export | `logs/traces/` |
| Evals | `evals/` | runner, graders, judge | entrypoint |

## Key invariants

Things that must stay true. Breaking one is an architecture change, not a bug fix.

1. `run_once` / `chat` signatures are stable — the eval suite depends on them.
2. `agent/model.py` is the only module that calls a language model.
3. Every span is written to `logs/traces/*.jsonl` regardless of backend.
4. Deterministic code never calls a model; model behavior is covered by evals.
5. <add project-specific invariants here>

## Data flow

<Numbered walkthrough of one representative request, naming the functions it
passes through. This is the single most useful section for an agent — it turns
"read the codebase" into "read six lines".>

1. ...

## State

<What is persisted where, what is per-request, what is per-conversation.>

## External dependencies

| Dependency | Used for | Failure mode | Fallback |
|------------|----------|--------------|----------|

## Known constraints

<Latency budget, cost ceiling, compliance limits, anything that rules out an
otherwise-obvious design. Recording these prevents an agent from "helpfully"
proposing something already ruled out.>

## Deliberately not done

<Approaches considered and rejected, one line each with the reason. This is the
cheapest possible way to stop a future agent re-proposing them.>
