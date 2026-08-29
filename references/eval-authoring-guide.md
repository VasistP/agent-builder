# Eval authoring guide

How to co-write good eval cases with the user, and the JSONL schemas
`evals/run_evals.py` expects.

## Working with the user

- One case at a time. Never invent ground truth or user turns.
- Start from `.agentbuilder/spec.md`: example requests → happy-path cases;
  feared failure modes → negative/safety cases; out-of-scope list → refusal cases.
- For each case, force these questions:
  - What must the response contain? What must it never contain?
  - Which tools should be called, with what arguments? How many steps max?
  - What is the latency / cost budget?
  - For conversations: what is the user's goal, and what does each turn expect?
- Prefer a deterministic grader. Only reach for the judge when the criterion is
  genuinely subjective (tone, helpfulness, groundedness phrasing).
- Tag every case: `capability`, `difficulty` (easy/med/hard), `data_source`,
  and `safety` (bool). Tags drive per-slice reporting (E2, E11, E13).

## `evals/single_response.jsonl`

One object per line:

```json
{
  "id": "sr-001",
  "input": "How many active enterprise customers did we have in Q2?",
  "goal": "Return the Q2 active enterprise customer count grounded in the CRM data.",
  "graders": [
    {"type": "tool_called", "name": "sql_query",
     "args_match": {"table": "customers"}, "max_steps": 3},
    {"type": "regex", "pattern": "\\b\\d[\\d,]*\\b"},
    {"type": "llm_judge", "rubric": "grounded-answer",
     "criteria": "Answer cites the CRM source and does not fabricate a number."}
  ],
  "latency_budget_s": 20,
  "tags": {"capability": "sql-qa", "difficulty": "med",
           "data_source": "crm", "safety": false}
}
```

## `evals/conversations.jsonl`

One object per line; `turns` is ordered:

```json
{
  "id": "cv-003",
  "goal": "User narrows a vague request into a specific report and gets it.",
  "turns": [
    {"user": "I need a report on churn.",
     "expect": [{"type": "llm_judge", "rubric": "asks-clarifying",
                 "criteria": "Agent asks which segment/timeframe before answering."}]},
    {"user": "Enterprise, last 2 quarters.",
     "expect": [{"type": "tool_called", "name": "sql_query"},
                {"type": "contains_all", "values": ["enterprise"]}]}
  ],
  "end_expect": [
    {"type": "goal_met", "rubric": "goal-check"},
    {"type": "no_redundant_loops"},
    {"type": "max_steps", "value": 8}
  ],
  "inject": [{"after_turn": 2, "tool_error": {"name": "sql_query"}}],
  "tags": {"capability": "clarification", "difficulty": "hard",
           "data_source": "crm", "safety": false}
}
```

`inject` (optional) forces a tool error so E5 recovery can be asserted.

## Grader catalogue

| type | deterministic? | checks |
|------|----------------|--------|
| `exact` | yes | output equals string |
| `regex` | yes | pattern matches / doesn't (`negate: true`) |
| `contains_all` / `contains_none` | yes | substrings present / absent |
| `json_schema` | yes | output parses and validates against schema |
| `tool_called` | yes | named tool invoked; optional `args_match`, `times` |
| `max_steps` | yes | agent step count ≤ value |
| `latency_budget` | yes | wall-clock ≤ value |
| `no_redundant_loops` | yes | no identical consecutive tool calls |
| `recovered_from_error` | yes | after injected error, agent retried/adapted and still met goal |
| `llm_judge` | no | rubric-scored; references `evals/rubrics/<id>.md` |
| `goal_met` | no (judge) | end state satisfies `goal` |

## Rubrics — `evals/rubrics/<id>.md`

```markdown
# Rubric: grounded-answer
PASS if all:
- The answer's key facts are supported by tool/retrieval output in the trace.
- No invented numbers, names, or dates.
- If data was insufficient, the agent said so rather than guessing.
FAIL otherwise. Output strictly: {"verdict": "pass"|"fail", "reason": "<1 sentence>"}
```

Keep rubrics binary (pass/fail + reason) for stable judging; aggregate to a rate.

## Judge alignment — `evals/judge_alignment.md`

Record: sample size, human labels, judge labels, agreement rate / kappa, rubric
changes made, judge model + params, date. Re-run when the judge model changes.
