"""Unit tests for model-tier routing. Deterministic: no model is involved."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from route_task import apply_floors, load_policy, match_tier, route  # noqa: E402


@pytest.fixture(scope="module")
def policy() -> dict:
    return load_policy()


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ("find where the sql builder lives", "nano"),
        ("explain what this function does", "nano"),
        ("regenerate the function index", "nano"),
        ("append a changelog entry", "nano"),
        ("implement the retry helper", "standard"),
        ("write a unit test for the parser", "standard"),
        ("redesign the retrieval architecture", "deep"),
        ("root cause this intermittent failure", "deep"),
        ("threat model the tool registry", "deep"),
    ],
)
def test_tier_matching(task: str, expected: str, policy: dict) -> None:
    tier, _ = match_tier(task, policy)
    assert tier == expected


def test_highest_tier_wins_on_mixed_signals(policy: dict) -> None:
    # Mentions a cheap verb ("explain") and an expensive one ("architecture").
    tier, _ = match_tier("explain the architecture redesign", policy)
    assert tier == "deep"


def test_unmatched_task_uses_default_tier(policy: dict) -> None:
    tier, reason = match_tier("zzz qqq wobble", policy)
    assert tier == policy["default_tier"]
    assert "default" in reason


def test_floor_raises_tier_for_architecture(policy: dict) -> None:
    tier, raised = apply_floors("nano", ["docs/ARCHITECTURE.md"], policy)
    assert tier == "deep"
    assert raised is not None


def test_floor_never_lowers_tier(policy: dict) -> None:
    tier, raised = apply_floors("deep", ["evals/single_response.jsonl"], policy)
    assert tier == "deep"
    assert raised is None


def test_route_returns_model_for_provider(policy: dict) -> None:
    d = route("find the parser", provider="anthropic", policy=policy)
    assert d["tier"] == "nano"
    assert d["model"] == policy["providers"]["anthropic"]["nano"]


def test_route_applies_floor_end_to_end(policy: dict) -> None:
    d = route("explain the diagram", paths=["docs/ARCHITECTURE.md"], policy=policy)
    assert d["tier"] == "deep"
    assert d["floor"] is not None
