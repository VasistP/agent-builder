# Development methodology: TDD for deterministic code, tiered EDD for model behavior

_Default. Tier B in `references/override-registry.md` — changing it requires
`skills/override`._

## The rule

Split by determinism, because the premise behind test-first only holds on one
side of that line.

| Layer | Method | Ordering |
|-------|--------|----------|
| Deterministic code (parsers, query builders, state reducers, tool arg/result handling, redaction, cost math) | **strict TDD** | write the failing test **before** the implementation, always |
| Model behavior (what the agent decides, says, calls, refuses) | **tiered EDD** | Tier 1 cases before code; Tier 2 cases harvested after first contact |

**Merge gate (both layers):** nothing merges without *both* a deterministic test
covering the non-LLM logic touched *and* at least one eval case covering the
behavior, whichever tier it came from.

## Why the split

Test-first assumes you can specify correct behavior before writing the code. For
a SQL builder that's completely true. For model behavior it's only partly true:
you know the *criteria* up front, but you don't know *which failure modes are
real* until you've watched the model fail. Cases written purely from imagination
test the failures you predicted, not the ones you have.

That matters here because eval authoring is the single most expensive resource
in this framework — `skills/3-evalset` explicitly warns the user they must sit
there and supply real ground truth. Spending all of it before the agent has ever
run once mis-allocates it, and anchors the suite slightly off-target.

The counter-argument — "if you don't write evals first you never write them" — is
real, and it's the reason EDD is in here at all. But this framework already
solves that **structurally**: phase 3 precedes phase 5, the CI gate blocks merges,
and every phase ends at a human checkpoint. Discipline comes from the gate, not
from the corpus size. So you can afford to be deliberate about which cases you
write when.

The distinction that actually matters is **harness-first, not corpus-first**.

## Eval tiers

Every case carries `"tier": 1 | 2` and a `"source"`.

### Tier 1 — specification cases (written before agent code)

Target ~30% of the planned suite. Derived directly from `.agentbuilder/spec.md`:

- **Example requests** → happy-path task-completion cases.
- **Out of scope** list → refusal cases.
- **Feared failure modes** → negative cases.
- **Constraints** → latency/step-budget/cost cases.
- **Data sources** → tool-selection and groundedness cases.

These are things you genuinely know before building, they're cheap to write, and
they're stable — they rarely need rewriting once the agent exists.

`"source": "spec"`

### Tier 2 — discovered cases (written after first contact)

The remaining ~70%, harvested once the agent runs for real:

- Failures seen in `logs/traces/` during phase 5 and each phase 6 feature.
- Wrong-tool-then-recover trajectories.
- Loops, stalls, and step-budget blowouts.
- Anything a human reviewer flagged at a checkpoint.
- Production traffic once there is any (`eval-standards.md` E10).

These are where most of the suite's real value lives.

`"source": "trace:<trace_id>"` or `"source": "checkpoint:<phase>"` — keep the
provenance so you can tell imagined cases from observed ones.

## Per-feature loop ordering

`skills/6-feature` enforces this order. Note that **both** kinds of test come
before implementation:

1. Pick one feature; restate acceptance criteria.
2. `fn_search` to locate the code.
3. **Write Tier 1 eval cases** for this feature's success + feared failures.
4. **Write the deterministic tests** for the non-LLM logic — they must fail.
5. Implement until the deterministic tests pass.
6. Refresh `FUNCTIONS.md`.
7. Run `make eval`; review traces.
8. **Harvest Tier 2 cases** from anything that failed or looked wrong.
9. Re-run; show the delta; human checkpoint.

Step 8 is the part teams skip, and it's the part that compounds. Don't let a
checkpoint pass with an unexplained eval failure and no new case recorded.

## Ratio health check

At each checkpoint, report the tier mix. A suite that stays >50% Tier 1 after
several features is a signal that nobody is harvesting real failures — flag it.
The healthy trajectory is Tier 1 heavy at phase 3, Tier 2 dominant by the third
or fourth feature.

## What this is not

**Spec-driven development is not an alternative to this** — it's upstream of it.
Phase 0 produces `.agentbuilder/spec.md`, and both Tier 1 evals and the feature
backlog derive from it. The spec is the source of truth; TDD and EDD are how the
layers below it get built.
