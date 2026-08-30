"""Guard the snapshot discipline for docs/ARCHITECTURE.md.

ARCHITECTURE.md is overwritten rather than appended to, so an agent always reads
one compact current-state description instead of a growing history. For that to
be safe, every version must survive as its own git commit.

This enforces the rule: the file must be committed and clean *before* it is
rewritten. Then each rewrite lands in a distinct commit, and
`git log -p docs/ARCHITECTURE.md` is the full history.

Per project policy this commits but never pushes — pushing is outward-facing and
can fail or surprise (no remote, protected branch, detached HEAD). Push at your
next checkpoint.

Usage:
    python tools/arch_snapshot.py --check     # may I rewrite it now?
    python tools/arch_snapshot.py --commit    # commit pending changes first
    python tools/arch_snapshot.py --history   # list past versions
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCH = "docs/ARCHITECTURE.md"


def _git(*args: str) -> tuple[int, str]:
    """Run a git command in the repo root; return (returncode, stdout)."""
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def is_repo() -> bool:
    """Return True if the project root is inside a git work tree."""
    code, out = _git("rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def is_dirty() -> bool:
    """Return True if ARCHITECTURE.md has uncommitted changes."""
    _, out = _git("status", "--porcelain", "--", ARCH)
    return bool(out.strip())


def is_tracked() -> bool:
    """Return True if ARCHITECTURE.md is tracked by git."""
    code, _ = _git("ls-files", "--error-unmatch", ARCH)
    return code == 0


def check() -> int:
    """Report whether ARCHITECTURE.md may be rewritten right now."""
    if not is_repo():
        print("Not a git repository — snapshot history cannot be preserved.")
        print("Run `git init` before changing the architecture.")
        return 1
    if not (ROOT / ARCH).exists():
        print(f"{ARCH} does not exist yet — creating it is fine.")
        return 0
    if not is_tracked():
        print(f"{ARCH} is untracked. Commit it first so the current state is preserved:")
        print(f"  git add {ARCH} && git commit -m 'docs: architecture snapshot'")
        return 1
    if is_dirty():
        print(f"{ARCH} has uncommitted changes.")
        print("Commit them before rewriting, so the previous version keeps its own commit:")
        print("  make arch-snapshot-commit")
        return 1
    print(f"OK — {ARCH} is committed and clean. Safe to rewrite.")
    print("After rewriting, commit again so this version gets its own entry in history.")
    return 0


def commit() -> int:
    """Commit any pending ARCHITECTURE.md changes so the old version is preserved."""
    if not is_repo():
        print("Not a git repository.", file=sys.stderr)
        return 1
    if not is_dirty():
        print(f"Nothing to commit — {ARCH} is already clean.")
        return 0
    code, out = _git("add", "--", ARCH)
    if code != 0:
        print(out, file=sys.stderr)
        return code
    code, out = _git("commit", "-m", "docs: snapshot architecture before rewrite", "--", ARCH)
    print(out)
    if code == 0:
        print("\nCommitted locally. Not pushed — push at your next checkpoint.")
    return code


def history() -> int:
    """List the commits that changed ARCHITECTURE.md, newest first."""
    if not is_repo():
        print("Not a git repository.", file=sys.stderr)
        return 1
    code, out = _git("log", "--oneline", "--follow", "--", ARCH)
    print(out or f"No history yet for {ARCH}.")
    print(f"\nFull diffs: git log -p --follow -- {ARCH}")
    return code


def main() -> int:
    """CLI entrypoint for the architecture snapshot guard."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="may I rewrite it now?")
    group.add_argument("--commit", action="store_true", help="commit pending changes first")
    group.add_argument("--history", action="store_true", help="list past versions")
    args = parser.parse_args()

    if args.commit:
        return commit()
    if args.history:
        return history()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
