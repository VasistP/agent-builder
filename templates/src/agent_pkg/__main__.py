"""CLI entrypoint: `python -m agent_pkg "your request"`."""

from __future__ import annotations

import sys

from agent_pkg.agent.run import run_once


def main() -> int:
    """Run a single request from the command line and print the response."""
    if len(sys.argv) < 2:
        print('usage: python -m agent_pkg "your request"', file=sys.stderr)
        return 2
    response = run_once(" ".join(sys.argv[1:]))
    print(response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
