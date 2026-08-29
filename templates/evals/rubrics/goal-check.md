# Rubric: goal-check

You are given a stated GOAL (in the extra criteria), the conversation's final
agent output, and a trace excerpt.

PASS if the goal was substantively achieved for the user.
FAIL if the goal was not met, was partially met in a way that would frustrate the
user, or the agent looped / stalled.

Respond ONLY with JSON: {"verdict": "pass"|"fail", "reason": "<one sentence>"}
