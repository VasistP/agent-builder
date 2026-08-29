"""Observability: OpenTelemetry GenAI-shaped spans plus a portable JSON export.

Import `span` and `record_llm_usage` from here. Every agent run, LLM call, tool
call, and retrieval step should be wrapped in a `span(...)`. Regardless of the
backend configured, every span is also written to `logs/traces/*.jsonl` (schema
in references/observability-standards.md) so the tool can be swapped later.
"""

from agent_pkg.observability.tracing import record_llm_usage, span

__all__ = ["span", "record_llm_usage"]
