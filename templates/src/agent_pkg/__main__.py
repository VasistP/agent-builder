"""CLI entrypoint: `python -m agent_pkg "your request"`, plus `--tools`."""

from __future__ import annotations

import sys

from agent_pkg.agent.run import run_once
from agent_pkg.tools.registry import posture_report


def main() -> int:
    """Run a single request from the command line and print the response."""
    if len(sys.argv) < 2:
        print(
            'usage: python -m agent_pkg "your request"\n'
            "       python -m agent_pkg --tools    # every tool's security posture",
            file=sys.stderr,
        )
        return 2
    if sys.argv[1] == "--tools":
        print(posture_report())
        return 0
    response = run_once(" ".join(sys.argv[1:]))
    print(response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
