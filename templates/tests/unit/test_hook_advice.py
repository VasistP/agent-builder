"""Unit tests for the model-routing hook advisory.

Regression coverage for a real bug: this logic originally lived inline in a
quoted shell string and raised SyntaxError on every prompt, silenced by a
2>/dev/null. The hook must stay testable and must never raise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from hook_advice import advise  # noqa: E402


def test_nano_task_gets_cheap_model_advice() -> None:
    lines = advise("find where the sql builder lives")
    assert lines, "nano tasks must produce advice"
    assert "nano-tier" in lines[0]
    assert any("fn_search" in line for line in lines)


def test_deep_task_gets_decomposition_advice() -> None:
    lines = advise("redesign the retrieval architecture")
    assert "deep-tier" in lines[0]
    assert any("nano-sized" in line for line in lines)


def test_standard_task_is_silent() -> None:
    # Advising on every ordinary turn is noise that trains people to ignore it.
    assert advise("implement the retry helper") == []


def test_empty_prompt_is_silent() -> None:
    assert advise("") == []
    assert advise("   ") == []


def test_never_raises_on_odd_input() -> None:
    for prompt in ["\\", "{", "🙂" * 50, "a" * 5000]:
        advise(prompt)  # must not raise
