# Rubric: grounded-answer

PASS if ALL hold:
- The answer's key facts are supported by tool/retrieval output visible in the trace excerpt.
- No invented numbers, names, dates, or citations.
- If the available data was insufficient, the agent said so instead of guessing.

FAIL otherwise.

Respond ONLY with JSON: {"verdict": "pass"|"fail", "reason": "<one sentence>"}
