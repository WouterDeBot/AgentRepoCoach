"""Tests for the ``compare`` CLI subcommand."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from agentrepocoach.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scores(total: float, components: dict[str, float]) -> dict:
    """Build a minimal score dict matching CLI JSON output shape."""
    return {
        "total": total,
        "language": "python",
        "weights": {name: 0.20 for name in components},
        "components": {
            name: {"score": score, "breakdown": {}}
            for name, score in components.items()
        },
    }


BASE = _make_scores(
    total=72.50,
    components={
        "navigability": 80.0,
        "error_quality": 60.0,
        "decision_queryability": 70.0,
        "test_quality": 75.0,
        "module_hygiene": 77.5,
    },
)

PR = _make_scores(
    total=78.80,
    components={
        "navigability": 85.0,
        "error_quality": 55.0,
        "decision_queryability": 80.0,
        "test_quality": 75.0,
        "module_hygiene": 89.0,
    },
)


@pytest.fixture()
def base_file(tmp_path: Path) -> Path:
    """Write BASE scores to a temp JSON file."""
    p = tmp_path / "base.json"
    p.write_text(json.dumps(BASE))
    return p


@pytest.fixture()
def pr_file(tmp_path: Path) -> Path:
    """Write PR scores to a temp JSON file."""
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(PR))
    return p


# ---------------------------------------------------------------------------
# AC-1: Accepts two positional arguments (base_file and pr_file)
# ---------------------------------------------------------------------------

class TestCompareSubcommand:
    """Tests for ``agentrepocoach compare base.json pr.json``."""

    def test_compare_prints_markdown_output(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # AC-1, AC-2, AC-3, AC-4: parses files, computes deltas, formats markdown
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 0
        out = capsys.readouterr().out
        # Should contain markdown table header from format_pr_comment
        assert "| Component" in out
        # Should contain score values
        assert "72.50" in out
        assert "78.80" in out

    def test_compare_shows_delta(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # AC-3: compare_scores computes deltas
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "+6.30" in out

    def test_compare_contains_marker(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # AC-4: format_pr_comment output includes marker
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "<!-- agentrepocoach -->" in out

    # AC-6: --json flag outputs raw comparison dict as JSON
    def test_compare_json_flag(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["compare", "--json", str(base_file), str(pr_file)])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "base_total" in data
        assert "pr_total" in data
        assert "delta" in data
        assert "component_deltas" in data
        assert data["base_total"] == 72.50
        assert data["pr_total"] == 78.80

    def test_compare_json_flag_has_improved_regressed(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["compare", "--json", str(base_file), str(pr_file)])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "improved" in data
        assert "regressed" in data
        assert "navigability" in data["improved"]
        assert "error_quality" in data["regressed"]


class TestCompareErrors:
    """Error handling for the compare subcommand."""

    def test_missing_base_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pr_file = tmp_path / "pr.json"
        pr_file.write_text(json.dumps(PR))
        rc = main(["compare", str(tmp_path / "nonexistent.json"), str(pr_file)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "not found" in err.lower() or "does not exist" in err.lower() or "error" in err.lower()

    def test_missing_pr_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        base_file = tmp_path / "base.json"
        base_file.write_text(json.dumps(BASE))
        rc = main(["compare", str(base_file), str(tmp_path / "nonexistent.json")])
        assert rc == 2

    def test_invalid_json_in_base(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        base_file = tmp_path / "base.json"
        base_file.write_text("not json {{{")
        pr_file = tmp_path / "pr.json"
        pr_file.write_text(json.dumps(PR))
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_invalid_json_in_pr(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        base_file = tmp_path / "base.json"
        base_file.write_text(json.dumps(BASE))
        pr_file = tmp_path / "pr.json"
        pr_file.write_text("not json")
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 2

    def test_json_missing_total_key(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        base_file = tmp_path / "base.json"
        base_file.write_text(json.dumps({"components": {}}))
        pr_file = tmp_path / "pr.json"
        pr_file.write_text(json.dumps(PR))
        rc = main(["compare", str(base_file), str(pr_file)])
        assert rc == 2


class TestExistingCLIStillWorks:
    """Regression: the existing CLI behavior must not break."""

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
