"""Unit tests for context compaction selection logic.

Only the deterministic parts are tested here: when to compact and which turns
survive verbatim. Producing the summary is a model call, so its quality belongs
to the eval suite — faking it here would give false confidence.
"""

from agent_pkg.agent.compaction import (
    CompactionPolicy,
    assemble_compacted,
    estimate_tokens,
    select_for_compaction,
    should_compact,
)


def test_token_estimate_scales_with_length() -> None:
    assert estimate_tokens(["a" * 400]) == 100
    assert estimate_tokens([]) == 0


def test_should_compact_only_past_the_trigger() -> None:
    policy = CompactionPolicy(trigger_tokens=100)
    assert not should_compact(["a" * 100], policy)  # 25 tokens
    assert should_compact(["a" * 400], policy)  # 100 tokens


def test_head_and_tail_survive_verbatim() -> None:
    policy = CompactionPolicy(keep_first_turns=2, keep_recent_turns=3)
    messages = [f"m{i}" for i in range(10)]
    head, middle, tail = select_for_compaction(messages, policy)
    assert head == ["m0", "m1"], "opening turns carry the task definition"
    assert tail == ["m7", "m8", "m9"], "recent turns are where precision matters"
    assert middle == ["m2", "m3", "m4", "m5", "m6"]


def test_short_conversation_is_not_compacted() -> None:
    # Compacting a short conversation costs a model call and gains nothing.
    policy = CompactionPolicy(keep_first_turns=2, keep_recent_turns=3)
    messages = ["m0", "m1", "m2"]
    head, middle, tail = select_for_compaction(messages, policy)
    assert middle == []
    assert head + tail == messages


def test_no_messages_are_lost_in_the_split() -> None:
    policy = CompactionPolicy(keep_first_turns=1, keep_recent_turns=2)
    messages = [f"m{i}" for i in range(7)]
    head, middle, tail = select_for_compaction(messages, policy)
    assert head + middle + tail == messages


def test_assembled_context_marks_the_summary() -> None:
    out = assemble_compacted(["m0"], "they chose Qdrant", ["m9"])
    assert out[0] == "m0"
    assert "COMPACTED HISTORY" in out[1]
    assert "they chose Qdrant" in out[1]
    assert out[-1] == "m9"
