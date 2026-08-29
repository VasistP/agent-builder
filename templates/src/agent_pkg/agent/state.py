"""Typed agent state and the public Response type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "tool"]


@dataclass
class Message:
    """A single conversation message."""

    role: Role
    content: str
    tool_name: str | None = None


@dataclass
class AgentState:
    """Mutable state threaded through the agent graph for one request/turn."""

    messages: list[Message] = field(default_factory=list)
    conversation_id: str = "default"
    scratchpad: dict[str, Any] = field(default_factory=dict)
    steps: int = 0
    max_steps: int = 8

    def add(self, role: Role, content: str, tool_name: str | None = None) -> None:
        """Append a message to the running transcript."""
        self.messages.append(Message(role=role, content=content, tool_name=tool_name))


@dataclass
class Response:
    """The result of an agent run: final text plus a light trace summary."""

    text: str
    conversation_id: str
    steps: int
    tool_calls: list[str] = field(default_factory=list)
