"""LLM judge for subjective graders.

Default provider is local Ollama (zero cost, offline). Switching to a hosted
provider requires setting EVAL_JUDGE_PROVIDER=anthropic AND accepting that every
`make eval` run then costs money. Keep judging binary (pass/fail + reason) for
stability; see references/eval-authoring-guide.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_RUBRIC_DIR = Path(__file__).resolve().parent / "rubrics"


def _load_rubric(rubric_id: str) -> str:
    """Return the rubric markdown for `rubric_id`, or '' if none exists."""
    path = _RUBRIC_DIR / f"{rubric_id}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _build_prompt(rubric_id: str, criteria: str, agent_output: str, context: str) -> str:
    """Assemble the judge prompt from rubric, criteria, context, and output."""
    return (
        f"{_load_rubric(rubric_id)}\n\n"
        f"Extra criteria: {criteria}\n\n"
        f"--- CONTEXT (trace excerpt) ---\n{context}\n\n"
        f"--- AGENT OUTPUT ---\n{agent_output}\n\n"
        'Respond ONLY with JSON: {"verdict": "pass"|"fail", "reason": "<one sentence>"}'
    )


def judge(rubric_id: str, criteria: str, agent_output: str, context: str = "") -> dict:
    """Return {"verdict": "pass"|"fail", "reason": str} for one grader check."""
    provider = os.getenv("EVAL_JUDGE_PROVIDER", "ollama").lower()
    model = os.getenv("EVAL_JUDGE_MODEL", "llama3.1:8b")
    prompt = _build_prompt(rubric_id, criteria, agent_output, context)

    if provider == "ollama":
        raw = _ollama(model, prompt)
    elif provider == "anthropic":
        raw = _anthropic(model, prompt)
    else:
        raise ValueError(f"unknown EVAL_JUDGE_PROVIDER: {provider}")

    try:
        data = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
        return {"verdict": data.get("verdict", "fail"), "reason": data.get("reason", "")}
    except (ValueError, KeyError):
        return {"verdict": "fail", "reason": f"unparseable judge output: {raw[:120]}"}


def _ollama(model: str, prompt: str) -> str:
    """Call a local Ollama model (temperature 0, fixed seed) and return raw text."""
    import ollama

    client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    resp = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "seed": 7},
    )
    return resp["message"]["content"]


def _anthropic(model: str, prompt: str) -> str:  # pragma: no cover - paid path
    """Call a hosted Anthropic model as judge. Every call costs money."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model, max_tokens=256, messages=[{"role": "user", "content": prompt}]
    )
    return "".join(b.text for b in msg.content if b.type == "text")
