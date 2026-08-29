"""Ranked search over function names + docstrings in src/.

Use this FIRST when asked to change behavior: it points you at the function(s)
to edit with a fraction of the tokens of reading files.

Usage:
    python tools/fn_search.py "retry a failed tool call"
    python tools/fn_search.py --json "build the sql where clause"
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _entries() -> list[dict]:
    out: list[dict] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                out.append(
                    {
                        "location": f"{rel}:{node.lineno}",
                        "name": node.name,
                        "summary": doc.strip().splitlines()[0] if doc.strip() else "",
                        "haystack": _tokens(node.name.replace("_", " ") + " " + doc),
                    }
                )
    return out


def search(query: str, limit: int = 10) -> list[dict]:
    """Return the top `limit` functions scored by query-term overlap."""
    q = _tokens(query)
    scored = []
    for e in _entries():
        hay = e["haystack"]
        score = sum(hay.count(term) for term in q)
        score += sum(2 for term in q if term in e["name"].lower())
        if score:
            scored.append((score, e))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {"location": e["location"], "name": e["name"], "summary": e["summary"], "score": s}
        for s, e in scored[:limit]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    results = search(args.query, args.limit)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['location']:<45} {r['name']:<28} {r['summary']}")
        if not results:
            print("No matches. Try different terms or read FUNCTIONS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
