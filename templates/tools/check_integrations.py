"""Report which optional MCP servers and skills are available, and enable them on demand.

Nothing in `.agent/integrations.yml` is installed by default. This tool answers
"what have I got, what am I missing, and what would each unlock" — then adds only
what you ask for, after showing its vetting line.

Deliberate asymmetry between the two kinds of integration:

- **MCP servers** are detectable. `claude mcp list` reports configured servers and
  their health; project and user config files are read as a fallback.
- **Skills are not reliably detectable.** Built-in skills (dataviz, code-review,
  ...) are bundled rather than written to disk, so an empty `~/.claude/skills`
  proves nothing. This tool reports what it can see on disk and says plainly that
  the agent must check its own skill listing. Every skill therefore carries a
  fallback in the manifest so a phase still works without it.

Usage:
    python tools/check_integrations.py                    # status report
    python tools/check_integrations.py --json
    python tools/check_integrations.py --enable context7  # add one MCP server
    python tools/check_integrations.py --needed-by 2-observability
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / ".agent" / "integrations.yml"
PROJECT_MCP = ROOT / ".mcp.json"


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load the integrations catalogue."""
    src = path or MANIFEST
    data: dict[str, Any] = yaml.safe_load(src.read_text(encoding="utf-8"))
    return data


def configured_mcp_servers() -> set[str]:
    """Return MCP server names visible to the CLI or in project config.

    Tries `claude mcp list` first since it reflects what is actually loaded,
    including user-level and remote servers. Falls back to reading `.mcp.json`
    when the CLI is unavailable (CI, a different agent, no Claude Code).
    """
    names: set[str] = set()

    if shutil.which("claude"):
        try:
            proc = subprocess.run(
                ["claude", "mcp", "list"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            for line in proc.stdout.splitlines():
                if ":" in line and not line.startswith(("Checking", " ")):
                    names.add(line.split(":", 1)[0].strip())
        except (subprocess.SubprocessError, OSError):
            pass

    if PROJECT_MCP.exists():
        try:
            data = json.loads(PROJECT_MCP.read_text(encoding="utf-8"))
            names.update(data.get("mcpServers", {}).keys())
        except (OSError, json.JSONDecodeError):
            pass

    return names


def discoverable_skills() -> set[str]:
    """Return skill names found on disk.

    Incomplete by construction — built-in skills are not on the filesystem. Use
    only to confirm presence, never to conclude absence.
    """
    found: set[str] = set()
    roots = [
        Path.home() / ".claude" / "skills",
        ROOT / ".claude" / "skills",
        Path.home() / ".claude" / "plugins",
    ]
    for base in roots:
        if not base.exists():
            continue
        for skill_md in base.rglob("SKILL.md"):
            found.add(skill_md.parent.name)
    return found


def status(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build the availability report for every catalogued integration."""
    have_mcp = configured_mcp_servers()
    have_skills = discoverable_skills()

    mcp = {
        name: {
            **spec,
            "installed": name in have_mcp,
        }
        for name, spec in (manifest.get("mcp") or {}).items()
    }
    skills = {
        name: {
            **spec,
            "found_on_disk": name in have_skills,
        }
        for name, spec in (manifest.get("skills") or {}).items()
    }
    return {"mcp": mcp, "skills": skills}


def enable_mcp(name: str, manifest: dict[str, Any]) -> int:
    """Add one catalogued MCP server to the project `.mcp.json`, version-pinned.

    Refuses anything not in the manifest: an uncatalogued server has not been
    vetted, and adding it is a Tier B override (security S11).
    """
    spec = (manifest.get("mcp") or {}).get(name)
    if spec is None:
        print(f"{name!r} is not in .agent/integrations.yml.")
        print("Uncatalogued servers are unvetted — see references/mcp-catalogue.md.")
        return 1

    data: dict[str, Any] = {"mcpServers": {}}
    if PROJECT_MCP.exists():
        data = json.loads(PROJECT_MCP.read_text(encoding="utf-8"))
        data.setdefault("mcpServers", {})

    if name in data["mcpServers"]:
        print(f"{name} is already in .mcp.json")
        return 0

    pinned = f"{spec['package']}@{spec['version']}"
    data["mcpServers"][name] = {
        "//": f"{spec['enables']} Vetted {spec['vetted']}. {spec['risk']}",
        "command": "npx",
        "args": ["-y", pinned],
    }
    PROJECT_MCP.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"Added {name} -> {pinned} (pinned)")
    print(f"  enables: {spec['enables']}")
    print(f"  risk   : {spec['risk']}")
    print("\nRe-vet on any version bump — a bump is a new supply-chain event.")
    return 0


def _print_report(report: dict[str, Any], needed_by: str | None) -> None:
    def wanted(spec: dict[str, Any]) -> bool:
        return needed_by is None or needed_by in (spec.get("needed_by") or [])

    print("MCP servers (installed on demand, never by default)\n")
    for name, spec in report["mcp"].items():
        if not wanted(spec):
            continue
        mark = "installed" if spec["installed"] else "-"
        rec = spec.get("recommend", "optional")
        print(f"  [{mark:^9}] {name:<20} {rec}")
        print(f"              {spec['enables']}")
        if spec.get("condition"):
            print(f"              when: {spec['condition']}")
        if not spec["installed"]:
            print(f"              enable: make integrations-enable NAME={name}")
        print()

    print("Skills — used if available, with a fallback if not\n")
    for name, spec in report["skills"].items():
        if not wanted(spec):
            continue
        mark = "on disk" if spec["found_on_disk"] else "?"
        print(f"  [{mark:^9}] {name:<20} {spec['enables']}")
    print(
        "\n  '?' means not found on disk — built-in skills are bundled, not written\n"
        "  there, so this cannot prove absence. Check your own available-skills\n"
        "  listing; if a skill is genuinely missing, use the fallback in\n"
        "  .agent/integrations.yml rather than skipping the step."
    )


def main() -> int:
    """CLI entrypoint: report integration status, or enable one MCP server."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable", metavar="NAME", help="add a catalogued MCP server")
    parser.add_argument("--needed-by", metavar="PHASE", help="filter to one phase")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"No manifest at {MANIFEST}")
        return 1

    manifest = load_manifest()
    if args.enable:
        return enable_mcp(args.enable, manifest)

    report = status(manifest)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report, args.needed_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
