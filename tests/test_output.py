"""Tests for output comparison functions."""
from __future__ import annotations

from agentrepocoach.output import format_comparison, format_comparison_markdown, format_verbose


def _make_result(total: float, components: dict[str, float], language: str = "python") -> dict:
    """Build a minimal result dict for comparison testing."""
    return {
        "total": total,
        "language": language,
        "weights": {name: 0.20 for name in components},
        "components": {
            name: {"score": score, "breakdown": {}}
            for name, score in components.items()
        },
    }


BASELINE = _make_result(
    total=72.50,
    components={
        "navigability": 80.0,
        "error_quality": 60.0,
        "decision_queryability": 70.0,
        "test_quality": 75.0,
        "module_hygiene": 77.5,
    },
)

CURRENT = _make_result(
    total=78.80,
    components={
        "navigability": 85.0,
        "error_quality": 65.0,
        "decision_queryability": 80.0,
        "test_quality": 75.0,
        "module_hygiene": 89.0,
    },
)


class TestFormatComparison:
    """Tests for the terminal-friendly format_comparison function."""

    def test_shows_total_delta(self) -> None:
        """AC: Total score delta is displayed as 'baseline -> current (+delta)'."""
        output = format_comparison(CURRENT, BASELINE)
        assert "72.50" in output  # baseline
        assert "78.80" in output  # current
        assert "+6.30" in output  # delta

    def test_shows_per_component_deltas(self) -> None:
        """AC: Each component shows its delta."""
        output = format_comparison(CURRENT, BASELINE)
        # navigability went from 80 to 85 = +5.00
        assert "navigability" in output
        assert "+5.00" in output
        # test_quality stayed at 75 = +0.00
        assert "+0.00" in output

    def test_shows_negative_delta(self) -> None:
        """AC: Negative deltas are shown with minus sign."""
        worse = _make_result(
            total=70.00,
            components={
                "navigability": 75.0,
                "error_quality": 60.0,
                "decision_queryability": 70.0,
                "test_quality": 75.0,
                "module_hygiene": 70.0,
            },
        )
        output = format_comparison(worse, BASELINE)
        assert "-2.50" in output  # total delta 70 - 72.5

    def test_handles_identical_reports(self) -> None:
        """AC: Identical reports show zero deltas."""
        output = format_comparison(BASELINE, BASELINE)
        assert "+0.00" in output


class TestFormatComparisonMarkdown:
    """Tests for the markdown format_comparison_markdown function."""

    def test_produces_markdown_table(self) -> None:
        """AC: Output contains a markdown table with header row."""
        output = format_comparison_markdown(CURRENT, BASELINE)
        assert "| Component" in output
        assert "|---" in output

    def test_shows_total_delta_line(self) -> None:
        """AC: Markdown output shows total score delta."""
        output = format_comparison_markdown(CURRENT, BASELINE)
        assert "72.50" in output
        assert "78.80" in output
        assert "+6.30" in output

    def test_contains_marker_comment(self) -> None:
        """AC: Markdown output contains the agentrepocoach marker for PR comment updates."""
        output = format_comparison_markdown(CURRENT, BASELINE)
        assert "<!-- agentrepocoach -->" in output

    def test_shows_component_rows(self) -> None:
        """AC: Each component appears as a row in the table."""
        output = format_comparison_markdown(CURRENT, BASELINE)
        assert "navigability" in output
        assert "error_quality" in output
        assert "module_hygiene" in output


def _make_verbose_result(sub_max_key: str = "total") -> dict:
    """Build a minimal result dict for format_verbose testing.

    ``sub_max_key`` controls whether sub-component dicts use ``"total"`` or ``"max"``
    as the denominator key, mirroring the two conventions present in the codebase.
    """
    return {
        "total": 75.0,
        "language": "python",
        "weights": {"bootstrap_signals": 1.0},
        "components": {
            "bootstrap_signals": {
                "score": 75.0,
                "total": 100,
                "breakdown": {
                    "ci_signal": {
                        "score": 50.0,
                        sub_max_key: 50,
                        "workflows_found": 2,
                        "pr_trigger": True,
                    },
                    "readme_quality": {
                        "score": 25.0,
                        sub_max_key: 50,
                        "install_found": True,
                        "test_found": False,
                    },
                },
            }
        },
    }


class TestFormatVerboseDenominator:
    """GH-009 Bug 1: format_verbose must show correct denominator for sub-components."""

    def test_denominator_with_total_key(self) -> None:
        """AC-1: Sub-component dict using 'total' key shows correct denominator."""
        result = _make_verbose_result(sub_max_key="total")
        output = format_verbose(result)
        # ci_signal: 50.00 / 50 — denominator must NOT be 0
        assert "50.00 / 0" not in output
        assert "50.00 / 50" in output

    def test_denominator_with_max_key(self) -> None:
        """AC-1: Sub-component dict using legacy 'max' key also shows correct denominator."""
        result = _make_verbose_result(sub_max_key="max")
        output = format_verbose(result)
        assert "50.00 / 0" not in output
        assert "50.00 / 50" in output

    def test_total_key_not_in_extras(self) -> None:
        """AC-2: 'total' is excluded from the extras column (not duplicated after denominator)."""
        result = _make_verbose_result(sub_max_key="total")
        output = format_verbose(result)
        # The raw key 'total' must not appear in the extras dict portion of the line.
        # We check by verifying no line contains "'total'" (dict repr of the key).
        for line in output.splitlines():
            if "ci_signal" in line or "readme_quality" in line:
                assert "'total'" not in line, f"'total' leaked into extras: {line!r}"

    def test_max_key_not_in_extras(self) -> None:
        """AC-2: Legacy 'max' key is also excluded from the extras column."""
        result = _make_verbose_result(sub_max_key="max")
        output = format_verbose(result)
        for line in output.splitlines():
            if "ci_signal" in line or "readme_quality" in line:
                assert "'max'" not in line, f"'max' leaked into extras: {line!r}"


class TestFormatVerboseReadmeHeadLinesNote:
    """GH-009 Bug 2: readme_quality note surfaces scanned-line-count when checks fail."""

    def _make_readme_result(self, install_found: bool, test_found: bool, head_lines: int = 100) -> dict:
        note_val = (
            f"scanned first {head_lines} lines"
            " (configure readme_head_lines in .agentrepocoach.toml to extend)"
        ) if not install_found or not test_found else None

        readme_sub: dict = {
            "score": (25 if install_found else 0) + (25 if test_found else 0),
            "total": 50,
            "install_found": install_found,
            "test_found": test_found,
        }
        if note_val:
            readme_sub["note"] = note_val

        return {
            "total": readme_sub["score"],
            "language": "python",
            "weights": {"bootstrap_signals": 1.0},
            "components": {
                "bootstrap_signals": {
                    "score": readme_sub["score"],
                    "total": 100,
                    "breakdown": {"readme_quality": readme_sub},
                }
            },
        }

    def test_note_shown_when_install_missing(self) -> None:
        """AC-4: Note appears when install_found=False."""
        result = self._make_readme_result(install_found=False, test_found=True)
        output = format_verbose(result)
        assert "scanned first 100 lines" in output

    def test_note_shown_when_test_missing(self) -> None:
        """AC-4: Note appears when test_found=False."""
        result = self._make_readme_result(install_found=True, test_found=False)
        output = format_verbose(result)
        assert "scanned first 100 lines" in output

    def test_note_shown_when_both_missing(self) -> None:
        """AC-4: Note appears when both install_found and test_found are False."""
        result = self._make_readme_result(install_found=False, test_found=False)
        output = format_verbose(result)
        assert "scanned first 100 lines" in output

    def test_note_absent_when_both_found(self) -> None:
        """AC-4: Note is absent when both checks pass."""
        result = self._make_readme_result(install_found=True, test_found=True)
        output = format_verbose(result)
        assert "scanned first" not in output

    def test_note_mentions_toml_config(self) -> None:
        """AC-4: Note references .agentrepocoach.toml for user guidance."""
        result = self._make_readme_result(install_found=False, test_found=False)
        output = format_verbose(result)
        assert ".agentrepocoach.toml" in output

    def test_note_contains_configurable_line_count(self) -> None:
        """AC-4: Note reflects the configured readme_head_lines value."""
        result = self._make_readme_result(install_found=False, test_found=False, head_lines=200)
        output = format_verbose(result)
        assert "scanned first 200 lines" in output
