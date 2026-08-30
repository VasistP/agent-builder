"""Check that agent-builder's own markdown stays inside its context budgets.

The framework enforces line budgets on the context files it generates
(`templates/tools/context_budget.py`) but historically enforced nothing on
itself, and the orchestrator drifted from ~1,000 tokens to ~2,700 without anyone
noticing — a cost paid on every single invocation.

Budgets are in tokens rather than lines, because that is the resource actually
being spent, and they differ by how often a file loads:

    SKILL.md        loads on every invocation           tightest budget
    skills/*        loads when that phase runs          one at a time
    references/*    loads when the work needs it        largest, read rarely

Exceeding a budget is not automatically wrong; it is a prompt to ask whether the
excess is procedure (keep it, raise the budget deliberately) or rationale (move
it to a reference). Procedure belongs in SKILL.md, rationale in references/ —
see AGENTS.md.

Usage:
    python3 tools/skill_budget.py            # report
    python3 tools/skill_budget.py --check    # exit 1 if any file is over
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Characters per token for dense English markdown with tables and code fences.
#: Deliberately an estimate: the point is catching drift, not billing accuracy.
CHARS_PER_TOKEN = 3.7

#: (glob, budget in tokens, why this budget)
BUDGETS: tuple[tuple[str, int, str], ...] = (
    ("SKILL.md", 2200, "loads on every invocation"),
    ("skills/*/SKILL.md", 2400, "loads when that phase runs"),
    ("references/*.md", 6500, "read on demand, one or two per phase"),
)


def tokens(path: Path) -> int:
    """Estimate the token cost of a markdown file."""
    return round(len(path.read_text(encoding="utf-8")) / CHARS_PER_TOKEN)


def report() -> tuple[list[str], bool]:
    """Return (printable lines, over_budget) for every governed file."""
    lines: list[str] = []
    over = False
    for pattern, budget, why in BUDGETS:
        lines.append(f"\n{pattern}  — budget {budget:,} tokens ({why})")
        for path in sorted(ROOT.glob(pattern)):
            count = tokens(path)
            flag = "" if count <= budget else "   OVER"
            if count > budget:
                over = True
            rel = path.relative_to(ROOT)
            lines.append(f"  {str(rel):<46} {count:>6,}{flag}")
    if over:
        lines.append(
            "\nOver budget. Ask what the excess is: procedure stays and the budget"
            "\nmoves deliberately; rationale belongs in references/. See AGENTS.md."
        )
    return lines, over


def main() -> int:
    """Print the budget report; with --check, fail when anything is over."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if over budget")
    args = parser.parse_args()
    lines, over = report()
    print("\n".join(lines))
    return 1 if (over and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
