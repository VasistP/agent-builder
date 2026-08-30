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
import sys
import time
from collections import defaultdict
from collections.abc import Callable
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


def _record(case: dict, kind: str, runs: list[list[dict]]) -> dict:
    """Build one result record from a case's repeated runs.

    Both the agent and the LLM judge are non-deterministic, so a single run
    yields a pass/fail that is partly noise. Each case is executed `--runs`
    times and reported as a rate plus two consistency metrics:

    - ``pass_rate``: fraction of runs that passed (the headline number).
    - ``pass_all`` (pass^k): every run passed. The metric that matters for
      mission-critical behavior — an agent that works 2 times in 3 is broken.
    - ``pass_any`` (pass@k): at least one run passed. Useful for spotting
      capability that exists but is unreliable.
    """
    outcomes = [bool(checks) and all(c["passed"] for c in checks) for checks in runs]
    n = len(outcomes) or 1
    rate = sum(outcomes) / n
    return {
        "id": case["id"],
        "kind": kind,
        "tags": case.get("tags", {}),
        "tier": case.get("tier", 1),
        "source": case.get("source", "spec"),
        "runs": n,
        "outcomes": outcomes,
        "pass_rate": round(rate, 3),
        "pass_all": all(outcomes),
        "pass_any": any(outcomes),
        "passed": all(outcomes),  # strict: pass^k is the gate
        "checks": runs[0] if runs else [],
    }


def _errored(exc: Exception) -> list[dict]:
    """Represent a case that raised before it could be graded as a failed check."""
    return [
        {"grader": "agent_invocation", "passed": False, "detail": f"{type(exc).__name__}: {exc}"}
    ]


def _run_single(cases: list[dict], runs: int = 3) -> list[dict]:
    """Execute every single-response case `runs` times and grade each run.

    A run that raises is recorded as a failed run rather than aborting the
    suite — one broken case must not hide the results of every other case.
    """
    from agent_pkg.agent.run import run_once

    out = []
    for case in cases:
        attempts: list[list[dict]] = []
        for i in range(runs):
            start = time.time()
            try:
                resp = run_once(case["input"], conversation_id=f"{case['id']}-r{i}")
            except Exception as exc:  # noqa: BLE001 - recorded as a failed run
                attempts.append(_errored(exc))
                continue
            ctx = {
                "tool_calls": resp.tool_calls,
                "steps": resp.steps,
                "latency_s": time.time() - start,
                "trace_excerpt": " -> ".join(resp.tool_calls),
            }
            attempts.append(_grade_one(case.get("graders", []), resp.text, ctx))
        out.append(_record(case, "single", attempts))
    return out


def _run_conversations(cases: list[dict], runs: int = 3) -> list[dict]:
    """Execute every conversation case `runs` times, grading per-turn + end checks."""
    from agent_pkg.agent.run import chat

    out = []
    for case in cases:
        attempts: list[list[dict]] = []
        for i in range(runs):
            attempts.append(_one_conversation(case, i, chat))
        out.append(_record(case, "conversation", attempts))
    return out


def _one_conversation(case: dict, run_index: int, chat: Callable) -> list[dict]:
    """Run a single attempt at one conversation case; return its grader checks."""
    turns = [t["user"] for t in case["turns"]]
    start = time.time()
    try:
        responses = chat(turns, conversation_id=f"{case['id']}-r{run_index}")
    except Exception as exc:  # noqa: BLE001 - recorded as a failed run
        return _errored(exc)

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
    return checks


def _summarize(records: list[dict]) -> dict:
    """Aggregate pass rates overall, per tag=value slice, and per eval tier.

    Uses each case's ``pass_rate`` across runs rather than a single pass/fail, so
    the headline number reflects observed reliability instead of one sample.
    """
    by_tag: dict[str, list[float]] = defaultdict(list)
    for r in records:
        rate = r.get("pass_rate", float(r["passed"]))
        by_tag["overall"].append(rate)
        by_tag[f"tier={r.get('tier', 1)}"].append(rate)
        for k, v in r["tags"].items():
            by_tag[f"{k}={v}"].append(rate)
    return {k: round(sum(v) / len(v), 3) for k, v in by_tag.items() if v}


def _noise_band(records: list[dict]) -> float:
    """Estimate how much the overall pass rate moves from run-to-run variance.

    Per-case variance across k runs of a Bernoulli trial is p(1-p)/k. Averaging
    over n cases divides that by n; the band is ~2 standard errors. A delta
    inside this band is not evidence of a regression, and reporting it as one
    trains people to ignore the gate.
    """
    if not records:
        return 0.0
    variances = []
    for r in records:
        p = r.get("pass_rate", float(r["passed"]))
        k = max(r.get("runs", 1), 1)
        variances.append(p * (1 - p) / k)
    return round(2 * (sum(variances) / (len(records) ** 2)) ** 0.5, 3)


def _consistency(records: list[dict]) -> dict:
    """Report pass^k vs pass@k — the gap is unreliability, not incapability."""
    total = len(records) or 1
    always = sum(1 for r in records if r.get("pass_all", r["passed"]))
    ever = sum(1 for r in records if r.get("pass_any", r["passed"]))
    return {
        "pass_hat_k": round(always / total, 3),
        "pass_at_k": round(ever / total, 3),
        "flaky": ever - always,
    }


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
    parser.add_argument(
        "--runs",
        type=int,
        default=int(os.getenv("EVAL_RUNS", "3")),
        help="times to run each case; >1 is required to separate signal from noise",
    )
    args = parser.parse_args()

    if args.runs < 1:
        print("--runs must be at least 1", file=sys.stderr)
        return 2
    if args.runs == 1:
        print(
            "WARNING: --runs=1 cannot distinguish a regression from sampling noise.\n"
            "         Use it for a quick smoke check only, never as a merge gate."
        )

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
        records += _run_single(single, args.runs)
    if args.only != "single":
        records += _run_conversations(convos, args.runs)

    summary = _summarize(records)
    mix = _tier_mix(records)
    band = _noise_band(records)
    consistency = _consistency(records)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_sha": _git_sha(),
        "runs_per_case": args.runs,
        "judge_model": os.getenv("EVAL_JUDGE_MODEL", "unknown"),
        "agent_model": os.getenv("AGENT_MODEL", "unknown"),
        "counts": {"single": len(single), "conversation": len(convos)},
        "tier_mix": mix,
        "noise_band": band,
        "consistency": consistency,
        "summary": summary,
        "records": records,
    }
    out_path = RESULTS_DIR / f"{int(time.time())}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    prev = sorted(RESULTS_DIR.glob("*.json"))
    prev_summary = json.loads(prev[-2].read_text())["summary"] if len(prev) > 1 else {}

    print(
        f"\nEval results  (sha {payload['agent_sha']}, {len(records)} cases "
        f"x {args.runs} runs)  -> {out_path.name}"
    )
    print(f"  noise band (+/-): {band:.1%} — deltas smaller than this are not signal\n")

    regressions = []
    for tag, rate in sorted(summary.items()):
        delta = rate - prev_summary.get(tag, rate)
        if abs(delta) <= band:
            note = "  (~noise)" if delta else ""
        else:
            note = f"  ({delta:+.1%})"
            if delta < 0:
                regressions.append((tag, delta))
        print(f"  {tag:<28} {rate:6.1%}{note}")

    print(
        f"\n  Consistency: pass^k {consistency['pass_hat_k']:.1%} "
        f"(every run passed) vs pass@k {consistency['pass_at_k']:.1%} (any run passed)"
    )
    if consistency["flaky"]:
        print(
            f"  ! {consistency['flaky']} case(s) passed sometimes and failed sometimes. "
            "That is unreliability,\n    not incapability — treat it as a defect, not a "
            "rounding error."
        )

    print(f"\n  Tier mix: {mix['tier_1']} spec-derived / {mix['tier_2']} harvested from traces")
    if mix["tier_1_pct"] > 0.5 and len(records) > 5:
        print(
            "  ! Suite is still majority Tier 1 — are real failures being "
            "harvested? See references/methodology.md"
        )

    if regressions:
        print("\n  REGRESSION (beyond noise):")
        for tag, delta in regressions:
            print(f"    {tag} {delta:+.1%}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
