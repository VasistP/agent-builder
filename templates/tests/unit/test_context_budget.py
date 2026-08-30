"""Unit tests for context-file budgeting and rotation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import context_budget as cb  # noqa: E402


def test_split_preamble_separates_instructions_from_entries() -> None:
    lines = ["# Changelog", "", "> discipline note", "", "## 2026-01-01 — a", "body"]
    preamble, body = cb._split_preamble(lines)
    assert preamble == ["# Changelog", "", "> discipline note", ""]
    assert body[0].startswith("## ")


def test_split_preamble_with_no_entries_returns_everything() -> None:
    lines = ["# Changelog", "", "nothing yet"]
    preamble, body = cb._split_preamble(lines)
    assert preamble == lines
    assert body == []


def test_todo_entries_detected_as_list_items() -> None:
    lines = ["# TODO", "", "- [x] 1. done", "- [ ] 2. next"]
    preamble, body = cb._split_preamble(lines)
    assert preamble == ["# TODO", ""]
    assert len(body) == 2


def _write(root: Path, name: str, lines: list[str]) -> Path:
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _restore_budgets() -> None:
    """Keep BUDGETS mutations from leaking between tests."""
    original = dict(cb.BUDGETS)
    yield
    cb.BUDGETS.clear()
    cb.BUDGETS.update(original)


@pytest.fixture
def fake_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cb, "ROOT", tmp_path)
    monkeypatch.setattr(cb, "ARCHIVE", tmp_path / "docs" / "archive")
    return tmp_path


def test_rotation_keeps_newest_changelog_entries(fake_root: Path) -> None:
    preamble = ["# Changelog", ""]
    entries = [f"## day-{i}" for i in range(40)]  # newest-first ordering
    _write(fake_root, "docs/CHANGELOG.md", preamble + entries)
    monkey_budget = 12
    cb.BUDGETS["docs/CHANGELOG.md"] = (monkey_budget, True)

    dest = cb.rotate("docs/CHANGELOG.md")
    assert dest is not None

    kept = (fake_root / "docs/CHANGELOG.md").read_text().splitlines()
    archived = (fake_root / dest).read_text().splitlines()
    assert kept[:2] == preamble, "preamble must survive rotation"
    assert "## day-0" in kept, "newest entry stays in the live file"
    assert "## day-39" in archived, "oldest entry moves to the archive"
    assert "## day-39" not in kept


def test_rotation_is_noop_when_within_budget(fake_root: Path) -> None:
    _write(fake_root, "docs/TODO.md", ["# TODO", "", "- [ ] 1. only item"])
    cb.BUDGETS["docs/TODO.md"] = (250, True)
    assert cb.rotate("docs/TODO.md") is None


def test_non_rotatable_files_are_never_rotated(fake_root: Path) -> None:
    _write(fake_root, "AGENTS.md", ["# A"] + [f"line {i}" for i in range(500)])
    cb.BUDGETS["AGENTS.md"] = (10, False)
    assert cb.rotate("AGENTS.md") is None
    assert len((fake_root / "AGENTS.md").read_text().splitlines()) == 501


def test_report_flags_over_budget_files(fake_root: Path) -> None:
    _write(fake_root, "AGENTS.md", [f"line {i}" for i in range(40)])
    cb.BUDGETS.clear()
    cb.BUDGETS["AGENTS.md"] = (10, False)
    rows = cb.report()
    assert rows == [("AGENTS.md", 40, 10, True)]
