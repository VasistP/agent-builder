"""Durable execution: checkpointing, idempotency, and resume.

Agents have more failure points than ordinary services — orchestration, a
probabilistic model, tool calls, and human-in-the-loop pauses — and naive retry
logic handles none of them. Durable execution addresses this by persisting state
after every meaningful step so a run resumes from the last checkpoint rather than
from the beginning.

Two rules make retries safe:

1. **Checkpoint after every step** — each LLM call, tool return, and decision.
2. **Idempotency keys on side effects** — replaying a step must not duplicate the
   effect. A recorded result is reused rather than re-executed.

Human-in-the-loop maps onto the same primitives: an approval pause is just a
checkpoint that resumes when the decision arrives, which is what lets a run wait
hours or days without holding a process open.

This is a file-backed reference implementation, deliberately small. For
production scale, back `CheckpointStore` with Postgres, or delegate to a durable
execution engine (Temporal, Inngest, or LangGraph's own checkpointer) — the
interface is kept narrow so that swap is cheap.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Checkpoint:
    """One durable point in a run.

    Attributes:
        run_id: Stable id for the whole run; the resume key.
        step: Monotonic step counter within the run.
        state: Serializable agent state at this point.
        completed: Idempotency key -> recorded result, for replay-safe steps.
        pending_approval: Action awaiting a human decision, if suspended.
    """

    run_id: str
    step: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    completed: dict[str, Any] = field(default_factory=dict)
    pending_approval: dict[str, Any] | None = None


def idempotency_key(run_id: str, tool_name: str, arguments: dict[str, Any]) -> str:
    """Return a stable key identifying one side-effecting call.

    Derived from the run, the tool, and the exact arguments, so replaying the
    same step produces the same key and the recorded result is reused instead of
    the effect happening twice. Arguments are canonicalized (sorted keys) so
    dict ordering cannot produce two keys for one logical call.
    """
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(f"{run_id}|{tool_name}|{canonical}".encode()).hexdigest()
    return f"{tool_name}:{digest[:32]}"


class CheckpointStore:
    """File-backed checkpoint persistence, one JSON document per run."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory or os.getenv("CHECKPOINT_DIR") or "logs/checkpoints")

    def _path(self, run_id: str) -> Path:
        safe = "".join(c for c in run_id if c.isalnum() or c in "-_")[:128]
        return self.directory / f"{safe}.json"

    def save(self, checkpoint: Checkpoint) -> None:
        """Persist a checkpoint, replacing any earlier one for the same run."""
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(checkpoint.run_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(checkpoint), indent=2, default=str), encoding="utf-8")
        tmp.replace(path)  # atomic, so a crash mid-write cannot corrupt the run

    def load(self, run_id: str) -> Checkpoint | None:
        """Return the stored checkpoint for `run_id`, or None if there is none."""
        path = self._path(run_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Checkpoint(**data)

    def delete(self, run_id: str) -> None:
        """Remove a run's checkpoint once it has completed successfully."""
        self._path(run_id).unlink(missing_ok=True)


def run_once_idempotent(
    checkpoint: Checkpoint,
    tool_name: str,
    arguments: dict[str, Any],
    action: Any,
) -> Any:
    """Execute a side-effecting action at most once per run, even across replays.

    Args:
        checkpoint: The run's current checkpoint; mutated to record the result.
        tool_name: Tool being invoked.
        arguments: Its arguments; part of the idempotency key.
        action: Zero-argument callable performing the effect.

    Returns:
        The recorded result if this step already ran, otherwise the fresh result.
    """
    key = idempotency_key(checkpoint.run_id, tool_name, arguments)
    if key in checkpoint.completed:
        return checkpoint.completed[key]
    result = action()
    checkpoint.completed[key] = result
    return result
