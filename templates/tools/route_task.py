"""Decide which model tier a task should run on, per .agent/model-policy.yml.

Exists because spending a high-reasoning model on mechanical work (locating code,
explaining it, regenerating an index) is the most common way an agent project
burns its token budget. Deterministic and pure, so it is unit-tested.

Usage:
    python tools/route_task.py "find where the sql builder lives"
    python tools/route_task.py "redesign retrieval" --provider anthropic
    python tools/route_task.py "update the changelog" --json
    python tools/route_task.py "tweak the graph" --paths docs/ARCHITECTURE.md
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / ".agent" / "model-policy.yml"
TIER_ORDER = ["nano", "standard", "deep"]


def load_policy(path: Path | None = None) -> dict[str, Any]:
    """Load and return the model policy document."""
    src = path or POLICY_FILE
    data: dict[str, Any] = yaml.safe_load(src.read_text(encoding="utf-8"))
    return data


def match_tier(task: str, policy: dict[str, Any]) -> tuple[str, str]:
    """Return (tier, reason) for a task description.

    The highest-cost tier whose patterns match wins, so an explicitly deep task
    is not downgraded just because it also mentions a cheap-sounding verb.
    """
    text = task.lower()
    hits: list[tuple[int, str, str]] = []
    for tier, spec in (policy.get("tiers") or {}).items():
        for pattern in spec.get("match", []):
            if re.search(pattern, text):
                rank = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
                hits.append((rank, tier, pattern))
                break
    if not hits:
        return policy.get("default_tier", "standard"), "no rule matched; using default tier"
    rank, tier, pattern = max(hits, key=lambda h: h[0])
    return tier, f"matched /{pattern}/"


def apply_floors(tier: str, paths: list[str], policy: dict[str, Any]) -> tuple[str, str | None]:
    """Raise `tier` to any floor required by the paths being touched."""
    raised: str | None = None
    for floor in policy.get("floors", []):
        glob = floor.get("path_glob", "")
        if not any(fnmatch.fnmatch(p, glob) for p in paths):
            continue
        min_tier = floor.get("min_tier", "standard")
        if TIER_ORDER.index(min_tier) > TIER_ORDER.index(tier):
            tier = min_tier
            raised = f"raised to {min_tier}: {floor.get('reason', glob)}"
    return tier, raised


def route(
    task: str,
    paths: list[str] | None = None,
    provider: str | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the routing decision for a task.

    Args:
        task: Natural-language description of the work.
        paths: Files the task will touch, used to apply tier floors.
        provider: Provider key in the policy; defaults to `default_provider`.
        policy: Pre-loaded policy, mainly for tests.

    Returns:
        Dict with `tier`, `model`, `provider`, `reason`, and `floor` keys.
    """
    pol = policy or load_policy()
    tier, reason = match_tier(task, pol)
    tier, floor = apply_floors(tier, paths or [], pol)
    prov = provider or pol.get("default_provider", "anthropic")
    model = (pol.get("providers", {}).get(prov) or {}).get(tier)
    return {
        "task": task,
        "tier": tier,
        "provider": prov,
        "model": model,
        "reason": reason,
        "floor": floor,
    }


def main() -> int:
    """CLI entrypoint: print the routing decision for a task description."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", help="natural-language description of the work")
    parser.add_argument("--paths", nargs="*", default=[], help="files the task will touch")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not POLICY_FILE.exists():
        print(f"No policy at {POLICY_FILE}", file=sys.stderr)
        return 1

    decision = route(args.task, args.paths, args.provider)
    if args.json:
        print(json.dumps(decision, indent=2))
    else:
        print(f"tier     : {decision['tier']}")
        print(f"model    : {decision['model']}  ({decision['provider']})")
        print(f"reason   : {decision['reason']}")
        if decision["floor"]:
            print(f"floor    : {decision['floor']}")
        if decision["tier"] == "deep":
            print("\nnote: spend this tier on the DECISION, then hand implementation to nano.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
