# TODO

> **Discipline: APPEND-ONLY, including plan changes.** Never rewrite or delete a
> past item. When the plan changes, append a new numbered item that names what it
> supersedes and why. The record of *why the plan moved* is the most expensive
> context to reconstruct, and the easiest to lose.
>
> Budget: 250 lines. `make context-rotate` archives completed items older than
> the most recent 50 to `docs/archive/TODO-<date>.md`.

Status markers: `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` superseded

Supersession format — note it on **both** items:

```markdown
- [-] 12. Add pgvector retrieval adapter — SUPERSEDED BY 13
- [~] 13. SUPERSEDES 12 — use Qdrant instead; pgvector recall was 0.61 on the
         2026-08 eval slice vs 0.84 for Qdrant. See CHANGELOG 2026-08-29.
```

Keep items **nano-sized**: one item should be completable by the cheapest model
tier in a single focused pass. If an item needs a design decision, split it into
a `deep`-tier decision item and several `nano` implementation items.

---

- [x] 1. Scaffold project, tooling, docstring gate, function index
- [x] 2. Wire observability: OTel GenAI spans + portable JSON export + dashboard
- [x] 3. Create Tier 1 eval sets (single-response + conversations)
- [x] 4. Build deterministic test suites (unit / regression / integration)
- [ ] 5. Agent skeleton: typed state, graph, tool registry, first traced call
- [ ] 6. Record baseline eval run
- [ ] 7. <first backlog feature from .agentbuilder/spec.md>
