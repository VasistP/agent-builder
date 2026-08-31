"""Typed agent state and the public Response type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "tool"]


@dataclass
class Message:
    """A single conversation message.

    Tool messages carry the arguments they were called with and whether the call
    errored. Evals grade on these (`tool_called.args_match`,
    `recovered_from_error`) and the LLM judge needs them as evidence, so dropping
    them makes those graders unable to see what actually happened.
    """

    role: Role
    content: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_error: str | None = None


@dataclass
class AgentState:
    """Mutable state threaded through the agent graph for one request/turn."""

    messages: list[Message] = field(default_factory=list)
    conversation_id: str = "default"
    scratchpad: dict[str, Any] = field(default_factory=dict)
    steps: int = 0
    max_steps: int = 8

    def add(
        self,
        role: Role,
        content: str,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_error: str | None = None,
    ) -> None:
        """Append a message to the running transcript."""
        self.messages.append(
            Message(
                role=role,
                content=content,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_error=tool_error,
            )
        )


@dataclass
class ToolEvent:
    """One tool invocation: what was called, with what, and what came back."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    error: str | None = None


@dataclass
class Response:
    """The result of an agent run: final text plus the trajectory.

    ``tool_calls`` stays a list of names for the graders and callers that only
    need that. ``tool_events`` is the full trajectory — arguments, outputs and
    errors — which is what groundedness and trajectory judging actually require.
    """

    text: str
    conversation_id: str
    steps: int
    tool_calls: list[str] = field(default_factory=list)
    tool_events: list[ToolEvent] = field(default_factory=list)
