"""Shared test fixtures and the no-model-call guard.

Deterministic tests must never call a language model (see
references/deterministic-testing.md). `_block_model_hosts` fails any test that
attempts an outbound request to a known model provider host.
"""

from __future__ import annotations

import socket

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden for regenerating regression golden files."""
    parser.addoption("--update-golden", action="store_true", default=False)

_BLOCKED_HOSTS = ("api.anthropic.com", "api.openai.com", "generativelanguage.googleapis.com")


@pytest.fixture(autouse=True)
def _block_model_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    real_getaddrinfo = socket.getaddrinfo

    def guarded(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        if any(blocked in str(host) for blocked in _BLOCKED_HOSTS):
            raise AssertionError(
                f"deterministic test attempted a model call to {host!r} — "
                "model behavior belongs in evals/, not tests/"
            )
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
