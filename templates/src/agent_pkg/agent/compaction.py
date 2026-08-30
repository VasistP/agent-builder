"""Runtime context compaction for long conversations.

Context is finite and has diminishing marginal returns, so the goal is the
smallest set of high-signal tokens that still supports the task. When a
conversation approaches the window, summarize and reinitialize from that summary
rather than truncating blindly.

What to keep versus discard is the whole art. Over-aggressive compaction loses
subtle but critical context, so the summary must preserve **decisions made,
unresolved questions, and established facts**, while discarding redundant
back-and-forth. Tune the compaction prompt on real traces: maximize recall first
so nothing important is dropped, then improve precision.

Note the deliberate split of responsibilities: choosing *when* to compact and
*which* turns survive verbatim is deterministic and tested here. Producing the
summary itself is a model call, so its quality is covered by evals — never by a
faked response in a test.
"""

from __future__ import annotations

from dataclasses import dataclass

COMPACTION_PROMPT = """\
Summarize the conversation so far for an agent that will continue the work with
only this summary as history. Preserve, in this order of priority:

1. Decisions made and the reasoning behind them.
2. Unresolved questions and blocked work.
3. Established facts, identifiers, and values retrieved from tools or data.
4. Constraints the user stated, including anything they ruled out.

Discard: pleasantries, superseded intermediate reasoning, and any content already
captured by a later message. Do not invent detail. If something is uncertain, say
so explicitly rather than resolving it.
"""


@dataclass
class CompactionPolicy:
    """When to compact and how much recent history survives verbatim.

    Attributes:
        trigger_tokens: Compact once estimated context exceeds this.
        keep_recent_turns: Most recent turns kept verbatim after compaction —
            recent context is where precision matters most.
        keep_first_turns: Earliest turns kept verbatim; the opening usually
            carries the task definition, which summaries tend to erode.
    """

    trigger_tokens: int = 60_000
    keep_recent_turns: int = 6
    keep_first_turns: int = 2


def estimate_tokens(messages: list[str]) -> int:
    """Roughly estimate token count from character length (~4 chars/token).

    Deliberately approximate: this decides *when* to compact, and a real
    tokenizer would couple the agent to one provider's tokenization.
    """
    return sum(len(m) for m in messages) // 4


def should_compact(messages: list[str], policy: CompactionPolicy) -> bool:
    """Return True if the conversation has grown past the compaction trigger."""
    return estimate_tokens(messages) >= policy.trigger_tokens


def select_for_compaction(
    messages: list[str], policy: CompactionPolicy
) -> tuple[list[str], list[str], list[str]]:
    """Split messages into (head_kept, to_summarize, tail_kept).

    The head and tail survive verbatim; the middle is what gets summarized. When
    the conversation is too short to split meaningfully, nothing is summarized —
    compacting a short conversation costs a model call and gains nothing.

    Returns:
        Tuple of (head kept verbatim, middle to summarize, tail kept verbatim).
    """
    head_n = min(policy.keep_first_turns, len(messages))
    tail_n = min(policy.keep_recent_turns, max(len(messages) - head_n, 0))
    middle = messages[head_n : len(messages) - tail_n]
    if not middle:
        return messages[:head_n], [], messages[head_n:]
    return messages[:head_n], middle, messages[len(messages) - tail_n :]


def assemble_compacted(head: list[str], summary: str, tail: list[str]) -> list[str]:
    """Rebuild the conversation from kept turns plus the generated summary."""
    marker = f"[COMPACTED HISTORY]\n{summary}\n[END COMPACTED HISTORY]"
    return [*head, marker, *tail]
