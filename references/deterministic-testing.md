# Deterministic testing philosophy

## The one rule

**Never fabricate model calls or model-dependent inputs to make a test pass.**

If a test needs a canned LLM response or a hand-written "user query that should
produce X" to assert behavior, that behavior belongs in the **eval suite**
(`skills/3-evalset`), not here. Faking it gives false confidence and, worse,
lets a real regression pass CI while the evals — the thing that actually measures
model behavior — are bypassed.

## What deterministic tests DO cover

Functions whose output is a pure function of their inputs, no network, no model:

- Parsers and serializers (SQL, JSON, config, tool results).
- Query / SQL builders — given structured params, assert the generated string.
- Retrieval ranking / re-ranking given a *fixed* candidate list and scores.
- Schema / input validation, guardrail regexes, PII redaction.
- Tool argument construction and tool result parsing.
- State reducers / graph state transitions given explicit state in.
- Prompt template rendering: variables in → exact string out (this tests the
  template, not the model).
- Cost and token accounting math.

## Splitting model-touching functions

A function like `answer_question(q)` that builds a prompt, calls the model, and
parses the result should be split:

```
build_prompt(q, context)        -> str        # deterministic test
parse_answer(raw_model_output)  -> Answer      # deterministic test (real fixture
                                                # outputs are fine as *inputs* to
                                                # a parser — you are testing the
                                                # parser, not generating them)
call_model(prompt) -> str                      # thin shim, no logic, covered by evals
answer_question(q) = parse_answer(call_model(build_prompt(q, ...)))  # covered by evals
```

Note the nuance in `parse_answer`: using a *real, previously observed* model
output as a fixture INPUT to test a parser is fine — you're testing parsing
logic. What's forbidden is inventing a model output to assert that "the agent
would then do X".

## Suites

- **unit** (`tests/unit/`) — one pure function, many input cases.
- **regression** (`tests/regression/`) — deterministic transforms compared to
  golden files in `tests/regression/golden/`; `--update-golden` regenerates,
  human reviews the diff.
- **integration** (`tests/integration/`) — deterministic components wired
  together against real data-store containers (Postgres, vector DB). Still **no
  model calls**. Marked `@pytest.mark.integration`.

## CI guarantees

- Runs with `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` unset.
- A guard fixture monkeypatches the HTTP transport and fails the run if any
  outbound request to a model provider host is attempted.
- Zero tokens, fully reproducible, fast enough for pre-commit.
