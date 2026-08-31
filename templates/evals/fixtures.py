"""Case fixtures: the `setup` and `inject` hooks eval cases declare.

An eval case can say `"setup": "Seed <DATA_SOURCE> with a record containing ..."`
or a conversation turn can say `"inject": "make the next tool call time out"`.
Those strings are instructions to a human reading the case — nothing can execute
prose. Registering a callable here is what makes them actually happen.

This matters most for the adversarial suite. An indirect-injection case whose
`setup` never ran tests an agent reading a clean data source: it passes, and the
pass means nothing. So a case declaring `setup` or `inject` with no fixture
registered is a **hard error**, not a skip — the suite refuses to report a result
it cannot stand behind.

Register by case id for a whole-case ``setup``, or ``"<case-id>#<turn index>"``
for a turn's ``inject``::

    from evals.fixtures import fixture

    @fixture("adv-002-indirect-injection")
    def _seed_poisoned_row():
        db.execute("INSERT INTO notes (body) VALUES (?)", [POISONED])
        yield                      # the case runs here
        db.execute("DELETE FROM notes WHERE body = ?", [POISONED])

Anything before the ``yield`` is setup; anything after is teardown and runs even
if the case fails. A plain function with no ``yield`` is treated as setup-only.

A turn fixture is entered immediately before its turn and torn down at the end of
the case, so a condition it stages (a failing tool, a poisoned document) persists
for the rest of the conversation rather than vanishing after one exchange::

    @fixture("advc-003-tool-error#1")     # before turn index 1
    def _break_the_search_tool():
        with patch_tool("search", side_effect=TimeoutError):
            yield
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from typing import Any

_REGISTRY: dict[str, Callable[[], Any]] = {}


class MissingFixtureError(RuntimeError):
    """A case declared `setup`/`inject` but nothing was registered to perform it."""


def fixture(case_id: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
    """Register the setup/teardown callable for one eval case id."""

    def register(fn: Callable[[], Any]) -> Callable[[], Any]:
        _REGISTRY[case_id] = fn
        return fn

    return register


def turn_key(case_id: str, turn_index: int) -> str:
    """Return the registry key for one turn's inject fixture."""
    return f"{case_id}#{turn_index}"


def is_registered(case_id: str) -> bool:
    """Return whether a fixture exists for this case id."""
    return case_id in _REGISTRY


@contextmanager
def applied(case: dict, *, what: str = "setup", key: str | None = None) -> Iterator[None]:
    """Run the case's registered fixture around the case body.

    Raises:
        MissingFixtureError: the case declares `setup`/`inject` but no fixture is
            registered for it. Failing loudly is the point — a silent skip turns
            an unperformed attack into a passing case.
    """
    reg_key = key or case["id"]
    if not is_registered(reg_key):
        raise MissingFixtureError(
            f'case {case["id"]!r} declares "{what}" but no fixture is registered\n'
            f"  under {reg_key!r}, so the {what} never happens and the case would\n"
            f"  pass without testing anything. Register one in evals/fixtures.py\n"
            f'  with @fixture({reg_key!r}), or remove the "{what}" key.'
        )
    fn = _REGISTRY[reg_key]
    result = fn()
    if isinstance(result, Generator):
        next(result)
        try:
            yield
        finally:
            for _ in result:  # drain teardown
                pass
    else:
        yield
