"""Turn a Claude Code hook payload into a model-routing advisory.

Called by .claude/hooks/model-guard.sh. Reads the hook JSON payload on stdin and
prints guidance for the model to read; prints nothing when there is nothing worth
saying. Never raises — a hook that fails must not disturb the user's prompt.

Kept as a real module rather than inline shell so it can be unit-tested; the
first version of this logic lived inside a quoted shell string and silently
failed with a SyntaxError for every prompt.

Usage (normally via the hook):
    echo '{"prompt": "redesign retrieval"}' | python tools/hook_advice.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NANO_ADVICE = (
    "Mechanical work — use the cheapest model. Locate code with "
    "tools/fn_search.py instead of reading files, and do not pull extra context."
)
DEEP_ADVICE = (
    "Spend the expensive tier on the DECISION only, then split the work into "
    "nano-sized tasks and run those cheaply. Record the outcome in "
    "docs/CHANGELOG.md, and if the architecture changed follow the snapshot "
    "discipline (make arch-snapshot) before rewriting docs/ARCHITECTURE.md."
)


def advise(prompt: str) -> list[str]:
    """Return advisory lines for a prompt, or [] if no advice is warranted.

    Silent for the default `standard` tier with no floor applied — emitting a
    note on every ordinary turn is noise that trains people to ignore it.
    """
    if not prompt.strip():
        return []
    try:
        from route_task import route

        decision = route(prompt)
    except Exception:  # noqa: BLE001 - advisory only; never break the prompt
        return []

    tier = decision.get("tier")
    floor = decision.get("floor")
    if tier == "standard" and not floor:
        return []

    lines = [f"[model-policy] This looks like a {tier}-tier task ({decision.get('reason')})."]
    if floor:
        lines.append(f"[model-policy] {floor}")
    if tier == "nano":
        lines.append(f"[model-policy] {NANO_ADVICE}")
    elif tier == "deep":
        lines.append(f"[model-policy] {DEEP_ADVICE}")
    return lines


def main() -> int:
    """Read the hook payload from stdin and print any advisory lines."""
    try:
        payload = json.load(sys.stdin)
        prompt = str(payload.get("prompt") or "")
    except Exception:  # noqa: BLE001 - malformed payload is not our problem
        return 0

    for line in advise(prompt.replace("\n", " ")[:500]):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
