"""Unit tests for PII redaction."""

from agent_pkg.observability.redaction import redact


def test_email_masked() -> None:
    assert redact("contact jane.doe@acme.com now") == "contact [EMAIL] now"


def test_nested_structures() -> None:
    out = redact({"a": ["call 555-12-3456", {"b": "x@y.co"}]})
    assert out == {"a": ["call [SSN]", {"b": "[EMAIL]"}]}


def test_non_string_passthrough() -> None:
    assert redact(42) == 42
