"""The single place the agent calls a language model.

Deliberately thin: no business logic lives here, so it is excluded from
deterministic coverage (see pyproject `omit`) and is exercised only by evals.
All model-dependent behavior must be measured by `evals/`, never faked in tests.
"""

from __future__ import annotations

import os

from agent_pkg.observability.tracing import record_llm_usage, span
from agent_pkg.pricing import cost_usd


class ModelNotConfigured(RuntimeError):
    """Raised when the agent is asked to call a model with no credentials set.

    The eval runner catches this to report a clean message instead of a traceback.
    """


#: Which env var holds the credential for each provider, and the default model.
#: `ollama` and `local` need no key — that is the whole point of supporting them,
#: and a scaffold that demands an Anthropic key from an Ollama project teaches
#: people to set a dummy value, which defeats the check entirely.
PROVIDERS: dict[str, tuple[str | None, str]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "claude-sonnet-5"),
    "openai": ("OPENAI_API_KEY", "gpt-4o"),
    "google": ("GOOGLE_API_KEY", "gemini-2.0-flash"),
    "azure": ("AZURE_OPENAI_API_KEY", "gpt-4o"),
    "ollama": (None, "llama3.1:8b"),
    "local": (None, "llama3.1:8b"),
}


def _provider() -> str:
    """Return the configured provider, validated against PROVIDERS."""
    name = os.getenv("AGENT_MODEL_PROVIDER", "anthropic").lower()
    if name not in PROVIDERS:
        raise ModelNotConfigured(
            f"AGENT_MODEL_PROVIDER={name!r} is not supported. "
            f"Choose one of: {', '.join(sorted(PROVIDERS))}."
        )
    return name


def _call_anthropic(model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
    """Call Anthropic; return (text, input_tokens, output_tokens)."""
    from anthropic import Anthropic  # local import keeps import-time deps light

    msg = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
        model=model,
        max_tokens=1024,
        system=system or _DEFAULT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    return text, msg.usage.input_tokens, msg.usage.output_tokens


def _call_openai(model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
    """Call an OpenAI-compatible endpoint; return (text, input_tokens, output_tokens)."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ModelNotConfigured(
            "this provider needs the OpenAI SDK: uv sync --extra openai"
        ) from exc

    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system or _DEFAULT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    usage = resp.usage
    return (
        resp.choices[0].message.content or "",
        getattr(usage, "prompt_tokens", 0),
        getattr(usage, "completion_tokens", 0),
    )


def _call_ollama(model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
    """Call a local Ollama server; return (text, input_tokens, output_tokens)."""
    import httpx

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    resp = httpx.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system or _DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=float(os.getenv("OLLAMA_TIMEOUT_S", "120")),
    )
    resp.raise_for_status()
    body = resp.json()
    return (
        body["message"]["content"],
        body.get("prompt_eval_count", 0),
        body.get("eval_count", 0),
    )


_DEFAULT_SYSTEM = "You are a helpful enterprise assistant."

_CALLERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "azure": _call_openai,
    "google": _call_openai,  # via an OpenAI-compatible gateway; replace if calling natively
    "ollama": _call_ollama,
    "local": _call_ollama,
}


def complete(prompt: str, *, system: str | None = None) -> str:
    """Return the model completion for `prompt`, emitting an OTel GenAI span.

    The provider comes from `AGENT_MODEL_PROVIDER` and decides both which
    credential is required and which client is used. Cost is only meaningful for
    hosted providers; a local model reports zero, which is accurate.

    Args:
        prompt: The fully rendered user prompt (built by deterministic code).
        system: Optional system prompt.

    Returns:
        The model's text response.

    Raises:
        ModelNotConfigured: If the provider is unknown, or its key is unset.
            Deterministic tests must never reach this function; evals are
            expected to.
    """
    provider = _provider()
    key_var, default_model = PROVIDERS[provider]
    model = os.getenv("AGENT_MODEL", default_model)

    if key_var and not os.getenv(key_var):
        raise ModelNotConfigured(
            f"AGENT_MODEL_PROVIDER={provider} but {key_var} is not set, so the agent "
            "cannot call a model.\n"
            "  Running evals?  Set it in .env — evals exercise the real model by design.\n"
            "  Using a local model instead?  Set AGENT_MODEL_PROVIDER=ollama; it needs "
            "no key.\n"
            "  Running tests?  Deterministic tests must not reach this function; the "
            "call belongs behind a split boundary (references/deterministic-testing.md)."
        )

    with span(
        "chat",
        operation="chat",
        attributes={"gen_ai.request.model": model, "gen_ai.system": provider},
        input_content={"system": system, "prompt": prompt},
    ) as s:
        text, in_tok, out_tok = _CALLERS[provider](model, prompt, system)
        cost = cost_usd(model, in_tok, out_tok)
        s["attributes"].update(
            {
                "gen_ai.usage.input_tokens": in_tok,
                "gen_ai.usage.output_tokens": out_tok,
                "cost.usd": cost,
            }
        )
        s["output"] = text
        record_llm_usage(in_tok, out_tok, model, cost)
        return text
