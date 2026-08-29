"""PII redaction applied to captured span content (observability O6).

Deterministic and pure — covered by tests/unit/test_redaction.py.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b\+?\d[\d ()-]{7,}\d\b"), "[PHONE]"),
]


def redact(value: Any) -> Any:
    """Return `value` with known PII patterns masked.

    Strings are scrubbed directly; dicts/lists are scrubbed recursively; other
    types are returned unchanged.
    """
    if isinstance(value, str):
        out = value
        for pattern, repl in _PATTERNS:
            out = pattern.sub(repl, out)
        return out
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    return value
