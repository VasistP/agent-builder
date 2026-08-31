"""Work out where an agent-builder project actually is, and what to do next.

Answers the question the framework was worst at: "I'm stuck — what now?" The
phase list alone cannot answer it, because the honest answer depends on what is
already on disk. This reads the project's real artifacts and reports the earliest
incomplete gate, so the recommendation is derived from evidence rather than from
asking the user to remember where they left off.

The filesystem is the primary evidence: what was actually built, and how far
through each phase it got. That is deliberate — it works on any project, needs no
bookkeeping, and cannot go stale.

`.agentbuilder/progress.md` is read **if it happens to exist**, purely as a bonus
signal about which phases a human approved. It has no required format and none is
imposed: the file is shaped by whoever wrote it for whatever kind of agent they
are building, so the parser takes any line that names a phase number next to a
checked box or the word "approved", and ignores everything else. When the file is
absent — the common case — approval is simply reported as unknown rather than as
a stack of warnings that would pressure people into maintaining a ledger.

Deliberately conservative: unclear evidence reports UNKNOWN rather than guessing
a phase complete. Telling someone to move on from a phase they have not finished
is the one wrong answer that costs more than saying "I am not sure".

Usage:
    python3 tools/next_step.py                  # inspect the current directory
    python3 tools/next_step.py --project ../my-agent
    python3 tools/next_step.py --json           # machine-readable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DONE, PARTIAL, TODO, UNKNOWN = "done", "partial", "todo", "unknown"

PHASES: tuple[tuple[int, str, str], ...] = (
    (0, "discovery", "agree the spec"),
    (1, "scaffold", "skeleton, tooling, context files"),
    (2, "observability", "spans, dashboard, JSON export"),
    (3, "evalset", "Tier 1 eval sets + judge"),
    (4, "testing", "deterministic suites"),
    (5, "agent-skeleton", "minimal traced agent loop"),
    (6, "feature", "one backlog feature per run"),
    (7, "security", "boundaries, tool scoping, injection evals"),
    (8, "adversarial", "red-team corpus + live session"),
)


@dataclass
class PhaseState:
    """One phase's status, the evidence behind it, and what remains."""

    number: int
    name: str
    status: str
    evidence: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    approved: bool | None = None  # None = no progress file; unknown, not "no"


def _read(path: Path) -> str:
    """Return a file's text, or empty string if it is missing or unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _jsonl(path: Path) -> list[dict]:
    """Return parsed JSONL rows, skipping blanks and malformed lines."""
    rows = []
    for line in _read(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


_PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_]{2,}>")


def _real_cases(path: Path) -> int:
    """Count eval cases that are neither shipped examples nor unspecialized."""
    n = 0
    for case in _jsonl(path):
        if case.get("example"):
            continue
        if _PLACEHOLDER.search(json.dumps(case, ensure_ascii=False, default=str)):
            continue
        n += 1
    return n


def approved_phases(root: Path) -> set[int] | None:
    """Return phases a human approved, or None when there is no progress file.

    None and empty-set mean different things and must not be conflated: None is
    "nobody recorded anything, judge by artifacts alone"; an empty set is "a
    progress file exists and records no approvals". Treating the first as the
    second would mark every finished phase as unapproved on the majority of
    projects, which is noise, and noise that pushes people toward bookkeeping
    this tool deliberately does not require.

    Parsed leniently by design — no format is imposed on the file.
    """
    text = _read(root / ".agentbuilder" / "progress.md")
    if not text.strip():
        return None
    found: set[int] = set()
    for line in text.splitlines():
        low = line.lower()
        if "- [x]" not in low and "approved" not in low and "complete" not in low:
            continue
        if match := re.search(r"phase\s*(\d)|^\s*[-*]\s*\[x\]\s*(\d)|\b(\d)\s*[—:-]", low):
            digit = next((g for g in match.groups() if g), None)
            if digit is not None:
                found.add(int(digit))
    return found


def _pkg_dir(root: Path) -> Path | None:
    """Return the project's source package directory, if the scaffold exists."""
    src = root / "src"
    if not src.is_dir():
        return None
    return next((p for p in sorted(src.iterdir()) if (p / "__init__.py").exists()), None)


def inspect(root: Path) -> tuple[list[PhaseState], list[str]]:
    """Return per-phase state and any blockers found in `root`."""
    ok = approved_phases(root)
    pkg = _pkg_dir(root)
    ab = root / ".agentbuilder"
    states: list[PhaseState] = []
    blockers: list[str] = []

    def add(n: int, status: str, evidence: list[str], remaining: list[str]) -> None:
        approved = None if ok is None else n in ok
        states.append(PhaseState(n, PHASES[n][1], status, evidence, remaining, approved))

    # 0 — discovery
    spec = ab / "spec.md"
    if spec.exists():
        backlog = len(re.findall(r"(?m)^\s*\d+\.\s+\S", _read(spec).split("Feature backlog")[-1]))
        add(0, DONE, [f"spec.md ({backlog} backlog features)"], [])
    else:
        add(0, TODO, [], ["no .agentbuilder/spec.md"])

    # 1 — scaffold
    have = [f for f in ("pyproject.toml", "Makefile", "AGENTS.md") if (root / f).exists()]
    if pkg and len(have) >= 2:
        add(1, DONE, [f"{', '.join(have)}, src/{pkg.name}/"], [])
    elif have:
        add(1, PARTIAL, have, ["scaffold incomplete"])
    else:
        add(1, TODO, [], ["no project skeleton"])

    # 2 — observability
    traces = list((root / "logs" / "traces").glob("*.jsonl")) if pkg else []
    span_count = sum(len(_read(t).splitlines()) for t in traces)
    if pkg and (pkg / "observability" / "exporter.py").exists():
        if span_count:
            plural = "span" if span_count == 1 else "spans"
            add(2, DONE, [f"exporter + {span_count} {plural} in logs/traces/"], [])
        else:
            add(2, PARTIAL, ["exporter present"], ["no traces yet — run a smoke call"])
    else:
        add(2, TODO, [], ["no observability module"])

    # 3 — evalset
    ev = root / "evals"
    single, convo = _real_cases(ev / "single_response.jsonl"), _real_cases(ev / "conversations.jsonl")
    if single or convo:
        ready = single >= 20 and convo >= 5
        tier1 = single >= 6 and convo >= 2
        add(
            3,
            DONE if ready else (PARTIAL if tier1 else PARTIAL),
            [f"{single} single, {convo} conversation cases"],
            [] if ready else [f"golden standard needs {max(0, 20 - single)} more single, "
                              f"{max(0, 5 - convo)} more conversations"],
        )
        if not tier1:
            states[-1].remaining.insert(0, "below the Tier 1 milestone (6 single, 2 conversations)")
    else:
        add(3, TODO, [], ["no eval cases"])

    # 4 — testing
    tests = list((root / "tests").rglob("test_*.py"))
    add(4, DONE if tests else TODO, [f"{len(tests)} test modules"] if tests else [],
        [] if tests else ["no deterministic tests"])

    # 5 — agent skeleton
    results = sorted((ev / "results").glob("*.json")) if ev.exists() else []
    graph = pkg / "agent" / "graph.py" if pkg else None
    if graph and graph.exists() and results:
        add(5, DONE, [f"agent loop + {len(results)} eval result(s)"], [])
    elif graph and graph.exists():
        add(5, PARTIAL, ["agent loop present"], ["no baseline eval run recorded"])
    else:
        add(5, TODO, [], ["no agent loop"])

    # 6 — features
    todo_txt = _read(root / "docs" / "TODO.md")
    open_items = len(re.findall(r"(?m)^\s*[-*]\s*\[ \]", todo_txt))
    add(6, PARTIAL if open_items else (DONE if results else TODO),
        [f"{open_items} open TODO items"] if open_items else [],
        [f"{open_items} features remain"] if open_items else [])

    # 7 — security
    if pkg and (pkg / "security").exists():
        gated = "side_effect=True" in _read(pkg / "tools" / "registry.py") or bool(
            list((pkg / "tools").glob("*.py")) and "permission=" in _read(pkg / "tools" / "registry.py")
        )
        add(7, DONE if gated else PARTIAL, ["security module present"],
            [] if gated else ["no tool declares a non-READ permission — run `make tools-posture`"])
    else:
        add(7, TODO, [], ["no security module"])

    # 8 — adversarial
    adv = _real_cases(ev / "adversarial.jsonl")
    adv_c = _real_cases(ev / "adversarial_conversations.jsonl")
    if adv or adv_c:
        need = adv >= 12 and adv_c >= 3
        add(8, DONE if need else PARTIAL, [f"{adv} adversarial, {adv_c} multi-turn"],
            [] if need else [f"needs {max(0, 12 - adv)} more adversarial, "
                             f"{max(0, 3 - adv_c)} more multi-turn"])
    else:
        add(8, TODO, [], ["red-team corpus not specialized"])

    # blockers
    overrides = _read(ab / "overrides.md")
    for line in overrides.splitlines():
        if "active" in line.lower() and "|" in line:
            blockers.append(f"active override: {line.strip()[:110]}")
    if pkg and not (root / ".env").exists() and (root / ".env.example").exists():
        blockers.append("no .env — copy .env.example before any eval run")
    return states, blockers


def next_step(states: list[PhaseState]) -> tuple[PhaseState, str]:
    """Return the phase to work on next and why it, rather than anything later.

    The earliest phase that is not both complete AND approved. Later phases build
    on earlier outputs, so jumping ahead means building against a moving target —
    which is the failure the phase order exists to prevent.
    """
    for state in states:
        if state.status in (PARTIAL, TODO, UNKNOWN):
            return state, "earliest incomplete phase; later phases build on its output"
        if state.approved is False:
            return state, "built but never approved at a checkpoint — confirm it before moving on"
    return states[-1], "everything is complete and approved; iterate phase 6 or re-run phase 8"


def render(root: Path, states: list[PhaseState], blockers: list[str]) -> str:
    """Return the human-readable status report."""
    lines = [f"agent-builder status — {root}", ""]
    if all(s.approved is None for s in states):
        lines.append("  (no progress file; judging from artifacts on disk)")
        lines.append("")
    for s in states:
        mark = {DONE: "x", PARTIAL: "~", TODO: " ", UNKNOWN: "?"}[s.status]
        approval = "   (not approved)" if s.approved is False and s.status == DONE else ""
        detail = "; ".join(s.evidence or s.remaining) or PHASES[s.number][2]
        lines.append(f"  [{mark}] {s.number} {s.name:<15} {detail}{approval}")
    if blockers:
        lines += ["", "Blockers"] + [f"  ! {b}" for b in blockers]
    target, why = next_step(states)
    lines += [
        "",
        f"NEXT: phase {target.number} — {target.name}",
        f"  why: {why}",
    ]
    for item in target.remaining:
        lines.append(f"  todo: {item}")
    lines += ["", f"Run `skills/{target.number}-{target.name}` for the step-by-step."]
    return "\n".join(lines)


def main() -> int:
    """Print the project's phase status and the single recommended next step."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".", help="project directory to inspect")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    states, blockers = inspect(root)
    target, why = next_step(states)
    if args.json:
        print(
            json.dumps(
                {
                    "project": str(root),
                    "phases": [asdict(s) for s in states],
                    "blockers": blockers,
                    "next": {"phase": target.number, "name": target.name, "why": why},
                },
                indent=2,
            )
        )
    else:
        print(render(root, states, blockers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
