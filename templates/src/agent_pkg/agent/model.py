"""The single place the agent calls a language model.

Deliberately thin: no business logic lives here, so it is excluded from
deterministic coverage (see pyproject `omit`) and is exercised only by evals.
All model-dependent behavior must be measured by `evals/`, never faked in tests.
"""

from __future__ import annotations

import os

from agent_pkg.observability.tracing import record_llm_usage, span
from agent_pkg.pricing import cost_usd


def complete(prompt: str, *, system: str | None = None) -> str:
    """Return the model completion for `prompt`, emitting an OTel GenAI span.

    Args:
        prompt: The fully rendered user prompt (built by deterministic code).
        system: Optional system prompt.

    Returns:
        The model's text response.

    Raises:
        RuntimeError: If no API key is configured (deterministic tests must not
            reach this function).
    """
    model = os.getenv("AGENT_MODEL", "claude-sonnet-5")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Model calls are covered by evals, not "
            "deterministic tests — see references/deterministic-testing.md."
        )

    with span(
        "chat",
        operation="chat",
        attributes={"gen_ai.request.model": model},
        input_content={"system": system, "prompt": prompt},
    ) as s:
        from anthropic import Anthropic  # local import keeps import-time deps light

        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system or "You are a helpful enterprise assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        in_tok, out_tok = msg.usage.input_tokens, msg.usage.output_tokens
        s["attributes"].update(
            {
                "gen_ai.usage.input_tokens": in_tok,
                "gen_ai.usage.output_tokens": out_tok,
                "cost.usd": cost_usd(model, in_tok, out_tok),
            }
        )
        s["output"] = text
        record_llm_usage(in_tok, out_tok, model, cost_usd(model, in_tok, out_tok))
        return text
