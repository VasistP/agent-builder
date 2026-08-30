"""Generate the agent-builder capabilities index from live repo state.

Answers "what can this framework do, and what can I invoke directly?" — read
from the actual skills, references, tools and integration manifest rather than a
hand-maintained list, so it cannot drift. Adding a phase or a reference doc makes
it appear here automatically.

Usage:
    python3 tools/capabilities.py            # print the index
    python3 tools/capabilities.py --write    # refresh CAPABILITIES.md
    python3 tools/capabilities.py --check    # exit 1 if CAPABILITIES.md is stale
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "CAPABILITIES.md"


def _frontmatter(path: Path) -> tuple[str, str]:
    """Return (name, description) from a SKILL.md front-matter block."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return path.parent.name, ""
    block = match.group(1)
    name = re.search(r"^name:\s*(.+)$", block, re.M)
    desc = re.search(r"^description:\s*>-\s*\n((?:\s{2,}.*\n?)+)", block, re.M)
    if desc:
        summary = " ".join(line.strip() for line in desc.group(1).splitlines())
    else:
        plain = re.search(r"^description:\s*(.+)$", block, re.M)
        summary = plain.group(1).strip() if plain else ""
    return (name.group(1).strip() if name else path.parent.name), summary


def _entry_paths(path: Path) -> list[str]:
    """Return which entry paths a sub-skill advertises (build / add / audit)."""
    text = path.read_text(encoding="utf-8").lower()
    section = text.split("## entry paths", 1)
    if len(section) < 2:
        return []
    body = section[1].split("\n## ", 1)[0]
    return [p for p in ("build", "add", "audit") if re.search(rf"\*\*{p}\*\*", body)]


_BOILERPLATE = re.compile(r"^Phase \d+ of agent-builder(,\s*repeatable)?\.\s*", re.I)


def _first_sentence(summary: str, limit: int = 130) -> str:
    """Return the first meaningful sentence, dropping the 'Phase N of…' prefix.

    Without the strip, every phase reads 'Phase 0 of agent-builder.' — accurate
    and entirely useless to someone asking what the framework can do.
    """
    summary = _BOILERPLATE.sub("", summary.strip())
    parts = re.split(r"(?<=\.)\s", summary)
    out = parts[0] if parts else summary
    if len(out) < 40 and len(parts) > 1:
        out = f"{out} {parts[1]}"  # very short lead sentence carries no information
    return out if len(out) <= limit else out[: limit - 1] + "…"


def collect_skills() -> list[dict]:
    """Return every sub-skill with its name, summary and entry paths."""
    rows = []
    for skill in sorted(ROOT.glob("skills/*/SKILL.md")):
        name, summary = _frontmatter(skill)
        rows.append(
            {
                "dir": skill.parent.name,
                "name": name,
                "summary": _first_sentence(summary),
                "entry_paths": _entry_paths(skill),
            }
        )
    return rows


def collect_references() -> list[dict]:
    """Return each reference doc's filename and title."""
    rows = []
    for ref in sorted(ROOT.glob("references/*.md")):
        first = next(
            (ln for ln in ref.read_text(encoding="utf-8").splitlines() if ln.startswith("# ")),
            "",
        )
        rows.append({"file": ref.name, "title": first.lstrip("# ").strip()})
    return rows


def collect_make_targets() -> list[dict]:
    """Return the scaffolded project's make targets and their help text."""
    makefile = ROOT / "templates" / "Makefile"
    if not makefile.exists():
        return []
    rows = []
    for line in makefile.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([a-zA-Z_-]+):.*?##\s*(.+)$", line)
        if m:
            rows.append({"target": m.group(1), "help": m.group(2).strip()})
    return rows


def collect_project_tools() -> list[dict]:
    """Return the CLI tools shipped into every scaffolded project."""
    rows = []
    for tool in sorted((ROOT / "templates" / "tools").glob("*.py")):
        doc = tool.read_text(encoding="utf-8").split('"""')
        summary = _first_sentence(doc[1].strip().splitlines()[0]) if len(doc) > 1 else ""
        rows.append({"file": f"tools/{tool.name}", "summary": summary})
    return rows


def _parse_integrations(text: str) -> dict[str, list[dict]]:
    """Extract name + `enables` per section from the integrations manifest.

    Deliberately dependency-free rather than using PyYAML. This tool has to run
    under whatever Python another coding agent happens to have, and the earlier
    PyYAML version silently dropped whole sections when the import failed —
    producing a confident, incomplete index, which is worse than an error.

    Handles only the manifest's actual shape: two levels of mapping plus scalar
    or folded (`>-`) `enables` values.
    """
    sections: dict[str, list[dict]] = {"mcp": [], "skills": []}
    current: str | None = None
    entry: str | None = None
    collecting = False
    buffer: list[str] = []

    def flush() -> None:
        if current and entry and buffer:
            sections[current].append({"name": entry, "enables": " ".join(buffer).strip()})

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0:
            flush()
            buffer, entry, collecting = [], None, False
            current = stripped.rstrip(":") if stripped.rstrip(":") in sections else None
            continue
        if current is None:
            continue

        if indent == 2 and stripped.endswith(":"):
            flush()
            buffer, collecting = [], False
            entry = stripped.rstrip(":")
            continue

        if indent >= 4 and stripped.startswith("enables:"):
            value = stripped[len("enables:") :].strip()
            if value in (">-", ">", "|", "|-"):
                collecting = True
                buffer = []
            else:
                buffer = [value]
                collecting = False
            continue

        if collecting and indent >= 6:
            buffer.append(stripped)
            continue
        if indent >= 4:
            collecting = False

    flush()
    return sections


def collect_integrations() -> dict[str, list[dict]]:
    """Return catalogued MCP servers and companion skills from the manifest."""
    manifest = ROOT / "templates" / ".agent" / "integrations.yml"
    if not manifest.exists():
        return {"mcp": [], "skills": []}
    parsed = _parse_integrations(manifest.read_text(encoding="utf-8"))
    return {
        kind: [{"name": e["name"], "enables": _first_sentence(e["enables"])} for e in entries]
        for kind, entries in parsed.items()
    }


def render() -> str:
    """Build the full capabilities index as markdown."""
    skills = collect_skills()
    phases = [s for s in skills if s["dir"][0].isdigit()]
    standalone = [s for s in skills if not s["dir"][0].isdigit()]
    integrations = collect_integrations()

    out: list[str] = [
        "# agent-builder capabilities",
        "",
        "Generated by `python3 tools/capabilities.py` from live repo state —",
        "never hand-edit. Adding a phase, reference or tool makes it appear here.",
        "",
        "Not using Claude Code? Nothing here needs a skill mechanism. Every skill",
        "is plain markdown: read `skills/<name>/SKILL.md` directly. See `AGENTS.md`.",
        "",
        "## Ways to invoke",
        "",
        "| Mode | Say something like | What happens |",
        "|------|--------------------|--------------|",
        '| full | "build me an agent for X" | phases 0-8 in order, human checkpoint between each |',
        '| targeted | "just set up evals" / "just observability" / "just '
        'security" | that phase only, against your existing repo — no '
        "re-scaffolding |",
        '| audit | "review our eval setup" / "red-team our agent" | scores what '
        "you have against the matching standards doc, returns prioritized gaps |",
        '| override | "we need to skip X" | the only way to change a locked default |',
        "",
        "Every phase below with an `audit` entry path can be pointed at an existing",
        "codebase — you do not have to have used this framework to build it.",
        "",
        "## Phases",
        "",
        "| # | Skill | Entry paths | What it does |",
        "|---|-------|-------------|--------------|",
    ]
    for s in phases:
        paths = ", ".join(s["entry_paths"]) or "build"
        out.append(f"| {s['dir'][0]} | `{s['dir']}` | {paths} | {s['summary']} |")

    if standalone:
        out += [
            "",
            "## Standalone skills — call these any time",
            "",
            "| Skill | What it does |",
            "|-------|--------------|",
        ]
        for s in standalone:
            out.append(f"| `{s['dir']}` | {s['summary']} |")

    tools = collect_project_tools()
    if tools:
        out += [
            "",
            "## Tools in every scaffolded project",
            "",
            "| Tool | Purpose |",
            "|------|---------|",
        ]
        for t in tools:
            out.append(f"| `{t['file']}` | {t['summary']} |")

    targets = collect_make_targets()
    if targets:
        out += ["", "## Make targets", "", "| Target | Purpose |", "|--------|---------|"]
        for t in targets:
            out.append(f"| `make {t['target']}` | {t['help']} |")

    if integrations["mcp"]:
        out += [
            "",
            "## MCP servers — catalogued, installed on demand",
            "",
            "Nothing is installed by default. `make integrations` shows status;",
            "`make integrations-enable NAME=x` adds one, version-pinned.",
            "",
            "| Server | Enables |",
            "|--------|---------|",
        ]
        for m in integrations["mcp"]:
            out.append(f"| `{m['name']}` | {m['enables']} |")

    if integrations["skills"]:
        out += [
            "",
            "## Companion skills — used if available, never required",
            "",
            "Each has a fallback in `.agent/integrations.yml`, so a missing skill",
            "degrades the step rather than skipping it.",
            "",
            "| Skill | Enables |",
            "|-------|---------|",
        ]
        for s in integrations["skills"]:
            out.append(f"| `{s['name']}` | {s['enables']} |")

    refs = collect_references()
    if refs:
        out += [
            "",
            "## Reference docs — read on demand",
            "",
            "| File | Covers |",
            "|------|--------|",
        ]
        for r in refs:
            out.append(f"| `references/{r['file']}` | {r['title']} |")

    out += [
        "",
        "## Out of scope",
        "",
        "Regulatory compliance and data governance, per-user data authorization",
        "(ACL-aware retrieval), and production deployment or secrets management.",
        "Real concerns for enterprise agents — they belong to compliance and",
        "platform owners, and this framework names them rather than",
        "half-implementing them.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    """CLI entrypoint: print, write, or drift-check the capabilities index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if content != current:
            print(
                "CAPABILITIES.md is stale. Run: python tools/capabilities.py --write",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.write:
        OUT.write_text(content, encoding="utf-8")
        print(f"Wrote {OUT.name}")
        return 0
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
