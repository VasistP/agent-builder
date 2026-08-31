"""Shared test fixtures and the no-model-call guard.

Deterministic tests must never call a language model (see
references/deterministic-testing.md). `_block_network` fails any test that
resolves a non-local host, or reaches a local model-server port.
"""

from __future__ import annotations

import socket

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --update-golden for regenerating regression golden files."""
    parser.addoption("--update-golden", action="store_true", default=False)


#: Hosts deterministic tests may still resolve. Everything else is blocked.
#:
#: This was an explicit blocklist of three provider hostnames, which meant a test
#: could reach a local Ollama, a self-hosted gateway, a proxy, Bedrock, or any
#: other endpoint and still be called "token-free". A deterministic suite is
#: defined by making no model call at all, so the guard is default-deny: any host
#: not listed here fails the test that touched it.
_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "::1", "")


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any deterministic test that resolves a non-local host.

    Local addresses stay resolvable so fixtures using temporary sockets keep
    working; a local model server is caught by the port check below rather than
    by the hostname, since it is on localhost by definition.
    """
    real_getaddrinfo = socket.getaddrinfo
    blocked_ports = {11434, 8000, 8080}  # ollama, common local model gateways

    def guarded(host, port=None, *args, **kwargs):  # type: ignore[no-untyped-def]
        name = str(host or "")
        if name not in _ALLOWED_HOSTS:
            raise AssertionError(
                f"deterministic test attempted a network call to {name!r} — "
                "model behavior belongs in evals/, not tests/. If this call is "
                "genuinely not a model call, stub it."
            )
        if port in blocked_ports:
            raise AssertionError(
                f"deterministic test attempted a call to a local model server "
                f"({name}:{port}) — that is still a model call. Use evals/."
            )
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
