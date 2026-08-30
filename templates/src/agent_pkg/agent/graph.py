"""Minimal agent loop: receive -> plan -> (tool?) -> respond.

`skills/5-agent-skeleton` replaces this with a full LangGraph graph. The shape
here is deliberately small so observability, evals, and tests can be verified
before real agent logic exists.
"""

from __future__ import annotations

from agent_pkg.agent.model import complete
from agent_pkg.agent.state import AgentState
from agent_pkg.observability.tracing import span
from agent_pkg.tools.registry import dispatch, is_tool_request


def render_prompt(state: AgentState) -> str:
    """Render the transcript into a single prompt string (deterministic).

    Covered by tests/unit/test_graph.py — this is string-in/string-out and does
    not depend on the model.
    """
    lines = [f"{m.role.upper()}: {m.content}" for m in state.messages]
    return "\n".join(lines) + "\nASSISTANT:"


def step(state: AgentState) -> AgentState:
    """Advance the agent by one step: maybe call a tool, then get a reply."""
    state.steps += 1
    with span(
        "agent run",
        operation="invoke_agent",
        attributes={"gen_ai.conversation.id": state.conversation_id},
    ):
        last_user = next((m.content for m in reversed(state.messages) if m.role == "user"), "")
        tool = is_tool_request(last_user)
        if tool and state.steps <= state.max_steps:
            with span(
                "execute_tool", operation="execute_tool", attributes={"tool.name": tool.name}
            ) as s:
                result = dispatch(tool.name, tool.arguments)
                s["output"] = result
            state.add("tool", result, tool_name=tool.name)
        reply = complete(render_prompt(state))
        state.add("assistant", reply)
    return state
