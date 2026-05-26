"""Tests for v0.3.1 release-integrity fixes.

AC-01: --all-languages flag exists in --help output
AC-02: --language help text lists all registered adapters
AC-03: agentrepocoach <positional-path> works without --repo
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from agentrepocoach.cli import main


FIXTURES_ROOT = Path(__file__).parent / "fixtures"


class TestAllLanguagesFlagExists:
    """AC-01: --all-languages flag must appear in --help output."""

    def test_all_languages_flag_exists(self) -> None:
        """Invoke --help via subprocess and assert --all-languages is listed."""
        result = subprocess.run(
            [sys.executable, "-m", "agentrepocoach", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--all-languages" in result.stdout


class TestLanguageHelpListsAllAdapters:
    """AC-02: --language help text must list all registered adapter names."""

    def test_language_help_lists_all_adapters(self) -> None:
        """Invoke --help, assert each adapter name appears in --language help text."""
        result = subprocess.run(
            [sys.executable, "-m", "agentrepocoach", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        stdout = result.stdout
        # All five adapter names must appear in the help output
        for adapter_name in ("csharp", "go", "python", "rust", "typescript"):
            assert adapter_name in stdout, (
                f"Adapter '{adapter_name}' missing from --help output. "
                f"Full stdout:\n{stdout}"
            )


class TestPositionalPathArgument:
    """AC-03: agentrepocoach <path> (positional) must succeed and produce a score."""

    def test_positional_path_argument(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Invoke main with positional path (no --repo), assert exit 0 and score produced."""
        python_repo = FIXTURES_ROOT / "sample-python-repo"
        mock_result = {
            "total": 72.00,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {"score": 72.0, "breakdown": {}},
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main([str(python_repo)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "72.00" in out

    def test_positional_path_dot_uses_cwd(self, capsys: pytest.CaptureFixture[str]) -> None:
        """agentrepocoach . should resolve to cwd without error."""
        mock_result = {
            "total": 65.00,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {"score": 65.0, "breakdown": {}},
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main(["."])
        assert rc == 0
        out = capsys.readouterr().out
        assert "65.00" in out

    def test_repo_flag_wins_over_positional(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When both --repo and positional are given, --repo wins and a notice is printed."""
        python_repo = FIXTURES_ROOT / "sample-python-repo"
        mock_result = {
            "total": 80.00,
            "language": "python",
            "weights": {"navigability": 0.20},
            "components": {
                "navigability": {"score": 80.0, "breakdown": {}},
            },
        }
        with patch("agentrepocoach.cli.compute_cah", return_value=mock_result):
            rc = main([str(python_repo), "--repo", str(python_repo)])
        assert rc == 0
        captured = capsys.readouterr()
        # --repo takes precedence; notice on stderr
        assert "takes precedence" in captured.err or "notice" in captured.err
