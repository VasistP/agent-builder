"""Deterministic token-cost math. Pure — covered by tests/unit/test_pricing.py."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PRICING_FILE = Path(__file__).resolve().parent.parent.parent / "evals" / "pricing.json"


@lru_cache
def _table() -> dict[str, dict[str, float]]:
    if _PRICING_FILE.exists():
        return json.loads(_PRICING_FILE.read_text(encoding="utf-8"))
    return {}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return USD cost for a call, using per-million-token rates in pricing.json.

    Unknown models return 0.0 (and should be added to evals/pricing.json).
    """
    rates = _table().get(model)
    if not rates:
        return 0.0
    return round(
        input_tokens / 1_000_000 * rates.get("input_per_mtok", 0.0)
        + output_tokens / 1_000_000 * rates.get("output_per_mtok", 0.0),
        6,
    )
