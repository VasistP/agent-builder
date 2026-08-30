"""Run the eval suite: single-response + conversation sets, mixed graders.

Runs on every change to agent code (pre-commit + CI). Writes a results file and
a trend row the observability dashboard reads. Prints overall + per-tag pass
rates and a diff vs the previous run.

    python evals/run_evals.py [--only single|conversation] [--tag capability=sql-qa]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

from evals.graders import run_grader
from evals.judge import judge

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "evals"
RESULTS_DIR = EVAL_DIR / "results"
JUDGE_GRADERS = {"llm_judge", "goal_met"}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _git_sha() -> str:
    """Return the short HEAD sha, or 'unknown' outside a repo / before any commit."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _grade_one(expect: list[dict], output: str, ctx: dict) -> list[dict]:
    """Run every grader spec in `expect` against one output; return check results."""
    results = []
    for spec in expect:
        if spec["type"] in JUDGE_GRADERS:
            verdict = judge(
                spec.get("rubric", "goal-check"),
                spec.get("criteria", ""),
                output,
                ctx.get("trace_excerpt", ""),
            )
            results.append(
                {
                    "grader": spec["type"],
                    "passed": verdict["verdict"] == "pass",
                    "detail": verdict["reason"],
                }
            )
        else:
            results.append(run_grader(spec, output, **ctx))
    return results


def _record(case: dict, kind: str, checks: list[dict]) -> dict:
    """Build one result record from a case and its grader checks."""
    return {
        "id": case["id"],
        "kind": kind,
        "tags": case.get("tags", {}),
        "tier": case.get("tier", 1),
        "source": case.get("source", "spec"),
        "passed": bool(checks) and all(c["passed"] for c in checks),
        "checks": checks,
    }


def _errored(exc: Exception) -> list[dict]:
    """Represent a case that raised before it could be graded as a failed check."""
    return [
        {"grader": "agent_invocation", "passed": False, "detail": f"{type(exc).__name__}: {exc}"}
    ]


def _run_single(cases: list[dict]) -> list[dict]:
    """Execute every single-response case and grade it.

    A case that raises is recorded as failed rather than aborting the run — one
    broken case must not hide the results of every other case.
    """
    from agent_pkg.agent.run import run_once

    out = []
    for case in cases:
        start = time.time()
        try:
            resp = run_once(case["input"], conversation_id=case["id"])
        except Exception as exc:  # noqa: BLE001 - recorded as a failed case
            out.append(_record(case, "single", _errored(exc)))
            continue
        ctx = {
            "tool_calls": resp.tool_calls,
            "steps": resp.steps,
            "latency_s": time.time() - start,
            "trace_excerpt": " -> ".join(resp.tool_calls),
        }
        checks = _grade_one(case.get("graders", []), resp.text, ctx)
        out.append(_record(case, "single", checks))
    return out


def _run_conversations(cases: list[dict]) -> list[dict]:
    """Execute every conversation case turn by turn and grade per-turn + end checks."""
    from agent_pkg.agent.run import chat

    out = []
    for case in cases:
        turns = [t["user"] for t in case["turns"]]
        start = time.time()
        try:
            responses = chat(turns, conversation_id=case["id"])
        except Exception as exc:  # noqa: BLE001 - recorded as a failed case
            out.append(_record(case, "conversation", _errored(exc)))
            continue
        checks: list[dict] = []
        for turn, resp in zip(case["turns"], responses, strict=False):
            ctx = {
                "tool_calls": resp.tool_calls,
                "steps": resp.steps,
                "latency_s": 0.0,
                "trace_excerpt": " -> ".join(resp.tool_calls),
            }
            checks += _grade_one(turn.get("expect", []), resp.text, ctx)
        final = responses[-1] if responses else None
        if final is not None:
            ctx = {
                "tool_calls": final.tool_calls,
                "steps": final.steps,
                "latency_s": time.time() - start,
                "trace_excerpt": " -> ".join(final.tool_calls),
            }
            checks += _grade_one(case.get("end_expect", []), final.text, ctx)
        out.append(_record(case, "conversation", checks))
    return out


def _summarize(records: list[dict]) -> dict:
    """Aggregate pass rates overall, per tag=value slice, and per eval tier."""
    by_tag: dict[str, list[bool]] = defaultdict(list)
    for r in records:
        by_tag["overall"].append(r["passed"])
        by_tag[f"tier={r.get('tier', 1)}"].append(r["passed"])
        for k, v in r["tags"].items():
            by_tag[f"{k}={v}"].append(r["passed"])
    return {k: round(sum(v) / len(v), 3) for k, v in by_tag.items() if v}


def _tier_mix(records: list[dict]) -> dict:
    """Return the Tier 1 / Tier 2 split, used as a suite-health signal.

    A suite still dominated by Tier 1 (spec-derived) cases after several features
    means nobody is harvesting real failures — see references/methodology.md.
    """
    total = len(records) or 1
    t1 = sum(1 for r in records if r.get("tier", 1) == 1)
    return {"tier_1": t1, "tier_2": total - t1, "tier_1_pct": round(t1 / total, 3)}


def _preflight() -> str | None:
    """Return a human-readable reason the suite cannot run, or None if it can.

    Checked before invoking the agent so a missing key produces one clear message
    rather than an identical failure recorded against every case.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return (
            "ANTHROPIC_API_KEY is not set, so the agent cannot be invoked.\n"
            "  Evals call the real model by design — set it in .env.\n"
            "  (The judge is separate and runs locally via Ollama by default.)"
        )
    provider = os.getenv("EVAL_JUDGE_PROVIDER", "ollama").lower()
    if provider == "ollama":
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            httpx.get(f"{host}/api/version", timeout=2.0).raise_for_status()
        except Exception:  # noqa: BLE001
            return (
                f"the local judge is not reachable at {host}.\n"
                "  Start it with `ollama serve` (native) or "
                "`docker compose --profile evals up -d ollama`."
            )
    elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return "EVAL_JUDGE_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set."
    return None


def main() -> int:
    """Load both eval sets, run them, persist results, and print the summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["single", "conversation"])
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    single = _load_jsonl(EVAL_DIR / "single_response.jsonl")
    convos = _load_jsonl(EVAL_DIR / "conversations.jsonl")

    if not single and not convos:
        print("No eval cases yet. Run skills/3-evalset to create them.")
        return 0

    if (problem := _preflight()) is not None:
        print(f"\nCannot run evals: {problem}")
        return 2

    records: list[dict] = []
    if args.only != "conversation":
        records += _run_single(single)
    if args.only != "single":
        records += _run_conversations(convos)

    summary = _summarize(records)
    mix = _tier_mix(records)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_sha": _git_sha(),
        "counts": {"single": len(single), "conversation": len(convos)},
        "tier_mix": mix,
        "summary": summary,
        "records": records,
    }
    out_path = RESULTS_DIR / f"{int(time.time())}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    prev = sorted(RESULTS_DIR.glob("*.json"))
    prev_summary = json.loads(prev[-2].read_text())["summary"] if len(prev) > 1 else {}

    print(f"\nEval results  (sha {payload['agent_sha']}, {len(records)} cases)  -> {out_path.name}")
    for tag, rate in sorted(summary.items()):
        delta = rate - prev_summary.get(tag, rate)
        arrow = f"  ({delta:+.3f})" if delta else ""
        print(f"  {tag:<28} {rate:6.1%}{arrow}")

    print(f"\n  Tier mix: {mix['tier_1']} spec-derived / {mix['tier_2']} harvested from traces")
    if mix["tier_1_pct"] > 0.5 and len(records) > 5:
        print(
            "  ! Suite is still majority Tier 1 — are real failures being "
            "harvested? See references/methodology.md"
        )

    return 0 if summary.get("overall", 0) >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
