"""Unit tests for on-demand integration discovery and enabling.

The load-bearing property: nothing installs by default, and an uncatalogued
(therefore unvetted) server cannot be added through this path.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import check_integrations as ci  # noqa: E402


@pytest.fixture
def manifest() -> dict:
    return ci.load_manifest()


def test_manifest_loads_and_catalogues_both_kinds(manifest: dict) -> None:
    assert manifest["mcp"], "expected MCP catalogue"
    assert manifest["skills"], "expected skill catalogue"


def test_every_mcp_entry_is_pinnable_and_vetted(manifest: dict) -> None:
    for name, spec in manifest["mcp"].items():
        assert spec.get("package"), f"{name} has no package"
        assert spec.get("version"), f"{name} is unpinned — see security S11"
        assert spec.get("vetted"), f"{name} has no vetting date"
        assert spec.get("risk"), f"{name} has no risk note"


def test_every_skill_has_a_fallback(manifest: dict) -> None:
    # Skills cannot be reliably detected, so a phase must still work without one.
    for name, spec in manifest["skills"].items():
        assert spec.get("fallback", "").strip(), f"{name} has no fallback"


def test_no_database_mcp_is_catalogued(manifest: dict) -> None:
    # Database servers are added only after discovery, with a read-only role.
    names = " ".join(manifest["mcp"]).lower()
    for banned in ("postgres", "mysql", "sqlite", "database"):
        assert banned not in names


class TestEnable:
    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ci, "PROJECT_MCP", tmp_path / ".mcp.json")

    def test_nothing_is_installed_by_default(self) -> None:
        assert not ci.PROJECT_MCP.exists()

    def test_enabling_writes_a_pinned_entry(self, manifest: dict) -> None:
        assert ci.enable_mcp("context7", manifest) == 0
        data = json.loads(ci.PROJECT_MCP.read_text())
        args = data["mcpServers"]["context7"]["args"]
        assert args[0] == "-y"
        assert "@" in args[1].rsplit("/", 1)[-1], "version must be pinned"

    def test_uncatalogued_server_is_refused(self, manifest: dict) -> None:
        assert ci.enable_mcp("totally-unvetted", manifest) == 1
        assert not ci.PROJECT_MCP.exists()

    def test_enabling_twice_is_idempotent(self, manifest: dict) -> None:
        ci.enable_mcp("context7", manifest)
        first = ci.PROJECT_MCP.read_text()
        assert ci.enable_mcp("context7", manifest) == 0
        assert ci.PROJECT_MCP.read_text() == first

    def test_enabling_preserves_existing_servers(self, manifest: dict) -> None:
        ci.enable_mcp("context7", manifest)
        ci.enable_mcp("memory", manifest)
        servers = json.loads(ci.PROJECT_MCP.read_text())["mcpServers"]
        assert {"context7", "memory"} <= servers.keys()


def test_status_marks_uninstalled_when_no_config(
    manifest: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ci, "PROJECT_MCP", tmp_path / "none.json")
    monkeypatch.setattr(ci, "configured_mcp_servers", lambda: set())
    report = ci.status(manifest)
    assert all(not s["installed"] for s in report["mcp"].values())


def test_skill_detection_never_claims_certainty(manifest: dict) -> None:
    # Built-ins are not on disk; the field name must not imply absence proof.
    report = ci.status(manifest)
    for spec in report["skills"].values():
        assert "found_on_disk" in spec
        assert "installed" not in spec
