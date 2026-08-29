"""Unit tests for deterministic graph helpers (no model calls)."""

from agent_pkg.agent.graph import render_prompt
from agent_pkg.agent.state import AgentState


def test_render_prompt_shape() -> None:
    state = AgentState()
    state.add("user", "hello")
    state.add("assistant", "hi")
    state.add("user", "bye")
    assert render_prompt(state) == "USER: hello\nASSISTANT: hi\nUSER: bye\nASSISTANT:"
