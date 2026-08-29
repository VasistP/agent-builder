"""Unit tests for tool registration and dispatch (deterministic paths)."""

import pytest

from agent_pkg.tools.registry import dispatch, is_tool_request


def test_echo_dispatch() -> None:
    assert dispatch("echo", {"text": "hi"}) == "hi"


def test_unknown_tool_raises() -> None:
    with pytest.raises(KeyError):
        dispatch("nope", {})


def test_parse_tool_request() -> None:
    req = is_tool_request("/echo some text")
    assert req is not None
    assert req.name == "echo"
    assert req.arguments == {"text": "some text"}


def test_non_tool_text_returns_none() -> None:
    assert is_tool_request("just a question") is None
