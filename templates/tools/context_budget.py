"""Keep the agent context files small enough to stay cheap to read.

AGENTS.md, ARCHITECTURE.md, CHANGELOG.md and TODO.md are read at the start of
most sessions. If they grow without bound they become the token cost they were
meant to prevent. This enforces per-file line budgets and rotates the
append-only files into docs/archive/ when they overflow.

Rotation preserves append-only semantics: nothing is edited or deleted, entries
are moved verbatim to an archive file that agents do not read by default. Git
retains everything either way.

Usage:
    python tools/context_budget.py --check     # report; exit 1 if over budget
    python tools/context_budget.py --rotate    # archive overflow, then report
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "docs" / "archive"

# file -> (budget_lines, rotatable)
BUDGETS: dict[str, tuple[int, bool]] = {
    "AGENTS.md": (150, False),
    "docs/ARCHITECTURE.md": (300, False),
    "docs/CHANGELOG.md": (200, True),
    "docs/TODO.md": (250, True),
}

# Entries start at a level-2 heading (CHANGELOG) or a list item (TODO).
_ENTRY_START = ("## ", "- [")


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def report() -> list[tuple[str, int, int, bool]]:
    """Return (name, actual_lines, budget, over_budget) for each tracked file."""
    out = []
    for name, (budget, _) in BUDGETS.items():
        n = len(_lines(ROOT / name))
        out.append((name, n, budget, n > budget))
    return out


def _split_preamble(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split a file into its instructional preamble and its entry body.

    The preamble (everything before the first entry) documents the file's write
    discipline and must survive rotation.
    """
    for i, line in enumerate(lines):
        if line.startswith(_ENTRY_START):
            return lines[:i], lines[i:]
    return lines, []


def rotate(name: str) -> str | None:
    """Move the oldest overflow entries of `name` into docs/archive/.

    Returns the archive path written, or None if the file was within budget.
    Keeps the preamble and the newest entries; never edits entry text.
    """
    budget, rotatable = BUDGETS[name]
    path = ROOT / name
    lines = _lines(path)
    if not rotatable or len(lines) <= budget:
        return None

    preamble, body = _split_preamble(lines)
    keep_budget = budget - len(preamble)
    if keep_budget <= 0:
        return None

    # CHANGELOG is newest-first, so keep the head. TODO is oldest-first, so keep
    # the tail. Both keep the preamble.
    newest_first = "CHANGELOG" in name
    kept = body[:keep_budget] if newest_first else body[-keep_budget:]
    moved = body[keep_budget:] if newest_first else body[:-keep_budget]
    if not moved:
        return None

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    stamp = _dt.date.today().isoformat()
    stem = Path(name).stem
    dest = ARCHIVE / f"{stem}-{stamp}.md"
    header = [
        f"# {stem} archive — rotated {stamp}",
        "",
        f"Entries moved verbatim out of `{name}` to keep it within its context",
        "budget. Nothing was edited. Agents do not read this file by default.",
        "",
    ]
    existing = _lines(dest)
    dest.write_text(
        "\n".join((existing or header) + ([""] if existing else []) + moved) + "\n",
        encoding="utf-8",
    )
    path.write_text("\n".join(preamble + kept).rstrip() + "\n", encoding="utf-8")
    return str(dest.relative_to(ROOT))


def main() -> int:
    """CLI entrypoint: check budgets, optionally rotating first."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--rotate", action="store_true")
    args = parser.parse_args()

    if args.rotate:
        for name, (_, rotatable) in BUDGETS.items():
            if rotatable and (dest := rotate(name)):
                print(f"rotated {name} -> {dest}")

    over = False
    for name, n, budget, is_over in report():
        flag = "OVER" if is_over else "ok"
        print(f"  {name:<24} {n:>4} / {budget:<4} lines  {flag}")
        over = over or is_over

    if over:
        print(
            "\nSome context files are over budget. Rotatable files: run "
            "`make context-rotate`.\nFor AGENTS.md / ARCHITECTURE.md, shorten them — "
            "detail belongs in docstrings,\nwhich fn_search can retrieve on demand."
        )
        return 1 if args.check else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
