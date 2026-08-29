"""Unit tests for deterministic cost math."""

from agent_pkg.pricing import cost_usd


def test_known_model_cost() -> None:
    # 1M input @ $3, 1M output @ $15
    assert cost_usd("claude-sonnet-5", 1_000_000, 1_000_000) == 18.0


def test_unknown_model_is_free() -> None:
    assert cost_usd("mystery-model", 5000, 5000) == 0.0


def test_zero_tokens() -> None:
    assert cost_usd("claude-sonnet-5", 0, 0) == 0.0
