"""Grader registry. Deterministic graders are pure and unit-tested."""

from evals.graders.deterministic import DETERMINISTIC_GRADERS, run_grader

__all__ = ["DETERMINISTIC_GRADERS", "run_grader"]
