"""Tests for the ``compare`` CLI subcommand and CLI integration."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

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


class TestCompareArgPositions:
    """Verify argument parsing order for the compare subcommand."""

    def test_json_flag_after_positional_args(
        self, base_file: Path, pr_file: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # --json after positional args should also work
        rc = main(["compare", str(base_file), str(pr_file), "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["base_total"] == 72.50
        assert data["pr_total"] == 78.80

    def test_compare_stderr_on_missing_both_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # When base file is missing, error should mention it (first check)
        rc = main(["compare", str(tmp_path / "a.json"), str(tmp_path / "b.json")])
        assert rc == 2
        err = capsys.readouterr().err
        assert "base file" in err.lower() or "does not exist" in err.lower()

    def test_json_missing_components_defaults_to_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # JSON with total but missing components -- compare_scores defaults
        # missing components to 0 and still succeeds.
        base = tmp_path / "base.json"
        base.write_text(json.dumps({"total": 50.0, "components": {}}))
        pr = tmp_path / "pr.json"
        pr.write_text(json.dumps(PR))
        rc = main(["compare", str(base), str(pr)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "50.00" in out
        assert "78.80" in out


class TestExistingCLIStillWorks:
    """Regression: the existing CLI behavior must not break."""

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_default_cli_repo_quiet(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main(["--repo", ".", "--quiet"]) should score a repo and print total."""
        # Mock compute_cah to avoid depending on actual repo structure
        mock_result = {
            "total": 65.00,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {"score": 65.0, "breakdown": {}},
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main(["--repo", ".", "--quiet"])
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert out == "65.00"

    def test_default_cli_repo_verbose(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main(["--repo", ".", "--verbose"]) should print verbose breakdown."""
        mock_result = {
            "total": 70.00,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {
                    "score": 70.0,
                    "breakdown": {
                        "structure": {
                            "score": 70.0,
                            "label": "Structure",
                            "tip": "Good structure",
                            "max_score": 100.0,
                        },
                    },
                },
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main(["--repo", ".", "--verbose"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "70.00" in out

    def test_default_cli_repo_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main(["--repo", "."]) without flags should print a summary."""
        mock_result = {
            "total": 75.50,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {"score": 75.5, "breakdown": {}},
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main(["--repo", "."])
        assert rc == 0
        out = capsys.readouterr().out
        assert "75.50" in out

    def test_default_cli_invalid_repo_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Passing a non-existent repo path should return error code 2."""
        rc = main(["--repo", "/nonexistent/path/to/repo"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()


class TestFormatWithoutOutput:
    """EXP-010: --format json/markdown prints to stdout without --output."""

    _MOCK_RESULT = {
        "total": 82.00,
        "language": "python",
        "weights": {"navigability": 0.20},
        "components": {
            "navigability": {"score": 82.0, "breakdown": {}},
        },
    }

    def test_format_json_prints_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--format json without --output prints JSON to stdout, exit 0."""
        with patch("agentrepocoach.cli.compute_cah", return_value=self._MOCK_RESULT):
            rc = main(["--repo", ".", "--format", "json"])
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.err == ""  # no stderr warning
        data = json.loads(captured.out)
        assert data["total"] == 82.00

    def test_format_markdown_prints_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--format markdown without --output prints markdown to stdout, exit 0."""
        with patch("agentrepocoach.cli.compute_cah", return_value=self._MOCK_RESULT):
            rc = main(["--repo", ".", "--format", "markdown"])
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.err == ""  # no stderr warning
        assert "### AgentRepoCoach" in captured.out
        assert "82.00" in captured.out

    def test_format_both_without_output_errors(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--format both without --output still requires --output and exits 2."""
        with patch("agentrepocoach.cli.compute_cah", return_value=self._MOCK_RESULT):
            rc = main(["--repo", ".", "--format", "both"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "error" in err.lower()

    def test_format_json_with_output_writes_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--format json --output path still writes to file (regression)."""
        out_file = tmp_path / "report.json"
        with patch("agentrepocoach.cli.compute_cah", return_value=self._MOCK_RESULT):
            rc = main(["--repo", ".", "--format", "json", "--output", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["total"] == 82.00
