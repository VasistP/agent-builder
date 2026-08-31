"""Public entrypoints: `run_once` (single-shot) and `chat` (multi-turn).

`evals/run_evals.py` calls these. Keep their signatures stable — the eval suite
and any external caller depend on them.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from agent_pkg.agent.graph import step
from agent_pkg.agent.state import AgentState, Response, ToolEvent


def run_once(request: str, *, conversation_id: str | None = None) -> Response:
    """Handle a single request and return the final response.

    Args:
        request: The user's request text.
        conversation_id: Optional id to correlate traces; generated if omitted.

    Returns:
        The agent's `Response` (final text + light trace summary).
    """
    state = AgentState(conversation_id=conversation_id or uuid.uuid4().hex)
    state.add("user", request)
    state = step(state)
    return _to_response(state)


def chat(turns: Iterable[str], *, conversation_id: str | None = None) -> list[Response]:
    """Run a sequence of user turns in one conversation, returning a Response per turn."""
    state = AgentState(conversation_id=conversation_id or uuid.uuid4().hex)
    out: list[Response] = []
    for turn in turns:
        state.add("user", turn)
        state = step(state)
        out.append(_to_response(state))
    return out


def _to_response(state: AgentState) -> Response:
    """Build a `Response` from the final assistant message and tool history."""
    text = next((m.content for m in reversed(state.messages) if m.role == "assistant"), "")
    events = [
        ToolEvent(
            name=m.tool_name,
            args=m.tool_args or {},
            output=m.content,
            error=m.tool_error,
        )
        for m in state.messages
        if m.role == "tool" and m.tool_name
    ]
    return Response(
        text=text,
        conversation_id=state.conversation_id,
        steps=state.steps,
        tool_calls=[e.name for e in events],
        tool_events=events,
    )
