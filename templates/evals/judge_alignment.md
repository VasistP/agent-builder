# Judge alignment record

Fill this in during `skills/3-evalset`. Re-run whenever `EVAL_JUDGE_MODEL` changes.

| Date | Judge model | Sample size | Agreement | Cohen's kappa | Rubric changes made |
|------|-------------|-------------|-----------|---------------|---------------------|
| _pending_ | | | | | |

## Method
1. Take ~15 real agent outputs spanning pass and fail.
2. The human owner labels each pass/fail against the rubric.
3. Run the judge on the same outputs.
4. Compute agreement + kappa. If agreement < ~0.8, revise the rubric wording and repeat.
5. Record the final numbers and the rubric diff here.
