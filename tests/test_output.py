"""Tests for output comparison functions."""
from __future__ import annotations

from agentrepocoach.output import format_comparison, format_comparison_markdown


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
