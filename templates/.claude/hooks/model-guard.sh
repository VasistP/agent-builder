#!/bin/sh
# UserPromptSubmit hook: classify the incoming request against
# .agent/model-policy.yml and inject the recommended tier into context.
#
# This is the one place the routing policy is applied automatically rather than
# relying on the agent to remember it. Other tools read the same policy through
# tools/route_task.py; see AGENTS.md.
#
# Contract: receives the hook payload as JSON on stdin; stdout is added to the
# model's context. Always exits 0 — a non-zero exit would block the user's
# prompt, which is far too aggressive for an advisory check.
#
# Wire it up in .claude/settings.json:
#   { "hooks": { "UserPromptSubmit": [
#       { "hooks": [ { "type": "command",
#                      "command": "sh .claude/hooks/model-guard.sh" } ] } ] } }
#
# Logic lives in tools/hook_advice.py rather than inline here: quoting Python
# inside a shell string is how this hook silently broke the first time.

set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

[ -f "$ROOT/.agent/model-policy.yml" ] || exit 0
[ -f "$ROOT/tools/hook_advice.py" ] || exit 0

if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
else
    PY=python3
fi

# Never let a hook failure interfere with the user's prompt.
"$PY" "$ROOT/tools/hook_advice.py" || true

exit 0
