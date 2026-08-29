"""Storage abstraction. Concrete adapters are added per the discovery spec.

Each adapter implements `Store` and gets: an integration test in
tests/integration/, and an observability `data_source` span attribute wherever
it is queried.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Store(Protocol):
    """Minimal contract every data-source adapter must satisfy."""

    name: str

    def health(self) -> bool:
        """Return True if the store is reachable and ready."""
        ...

    def query(self, request: Any) -> Any:
        """Execute a read against the store and return raw results."""
        ...
