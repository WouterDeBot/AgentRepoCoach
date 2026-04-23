"""Tests for the pr_bot module."""
from __future__ import annotations

import json

import pytest

from agentrepocoach.pr_bot import compare_scores, format_pr_comment, parse_score_output


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


# ---------------------------------------------------------------------------
# parse_score_output
# ---------------------------------------------------------------------------

class TestParseScoreOutput:
    """Tests for parse_score_output."""

    def test_parses_valid_json(self) -> None:
        raw = json.dumps(BASE)
        result = parse_score_output(raw)
        assert result["total"] == 72.50
        assert "components" in result

    def test_rejects_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_score_output("not json {{{")

    def test_rejects_missing_total(self) -> None:
        with pytest.raises(ValueError, match="missing required 'total'"):
            parse_score_output('{"components": {}}')


# ---------------------------------------------------------------------------
# compare_scores
# ---------------------------------------------------------------------------

class TestCompareScores:
    """Tests for compare_scores."""

    def test_total_delta(self) -> None:
        result = compare_scores(BASE, PR)
        assert result["base_total"] == 72.50
        assert result["pr_total"] == 78.80
        assert result["delta"] == pytest.approx(6.30)

    def test_component_deltas(self) -> None:
        result = compare_scores(BASE, PR)
        deltas_by_name = {d["name"]: d for d in result["component_deltas"]}
        assert deltas_by_name["navigability"]["delta"] == pytest.approx(5.0)
        assert deltas_by_name["error_quality"]["delta"] == pytest.approx(-5.0)
        assert deltas_by_name["test_quality"]["delta"] == pytest.approx(0.0)

    def test_improved_list(self) -> None:
        result = compare_scores(BASE, PR)
        assert "navigability" in result["improved"]
        assert "decision_queryability" in result["improved"]
        assert "module_hygiene" in result["improved"]

    def test_regressed_list(self) -> None:
        result = compare_scores(BASE, PR)
        assert "error_quality" in result["regressed"]

    def test_unchanged_not_in_improved_or_regressed(self) -> None:
        result = compare_scores(BASE, PR)
        assert "test_quality" not in result["improved"]
        assert "test_quality" not in result["regressed"]

    def test_identical_scores(self) -> None:
        result = compare_scores(BASE, BASE)
        assert result["delta"] == 0.0
        assert result["improved"] == []
        assert result["regressed"] == []

    def test_handles_missing_components_in_base(self) -> None:
        base_partial = _make_scores(total=50.0, components={"navigability": 80.0})
        pr_full = _make_scores(
            total=60.0,
            components={"navigability": 85.0, "error_quality": 70.0},
        )
        result = compare_scores(base_partial, pr_full)
        deltas_by_name = {d["name"]: d for d in result["component_deltas"]}
        # error_quality was absent in base (score 0), present in PR (70)
        assert deltas_by_name["error_quality"]["base_score"] == 0.0
        assert deltas_by_name["error_quality"]["pr_score"] == 70.0


# ---------------------------------------------------------------------------
# format_pr_comment
# ---------------------------------------------------------------------------

class TestFormatPrComment:
    """Tests for format_pr_comment."""

    def setup_method(self) -> None:
        self.comparison = compare_scores(BASE, PR)

    def test_contains_markdown_table(self) -> None:
        output = format_pr_comment(self.comparison)
        assert "| Component" in output
        assert "|---" in output

    def test_shows_total_delta(self) -> None:
        output = format_pr_comment(self.comparison)
        assert "72.50" in output
        assert "78.80" in output
        assert "+6.30" in output

    def test_shows_component_rows(self) -> None:
        output = format_pr_comment(self.comparison)
        assert "navigability" in output
        assert "error_quality" in output
        assert "module_hygiene" in output

    def test_delta_indicators_up(self) -> None:
        output = format_pr_comment(self.comparison)
        # navigability improved: should have ^ indicator
        for line in output.splitlines():
            if "navigability" in line:
                assert "^" in line
                break

    def test_delta_indicators_down(self) -> None:
        output = format_pr_comment(self.comparison)
        # error_quality regressed: should have v indicator
        for line in output.splitlines():
            if "error_quality" in line:
                assert "v" in line
                break

    def test_delta_indicators_equal(self) -> None:
        output = format_pr_comment(self.comparison)
        # test_quality unchanged: should have = indicator
        for line in output.splitlines():
            if "test_quality" in line:
                assert "=" in line
                break

    def test_contains_marker(self) -> None:
        output = format_pr_comment(self.comparison)
        assert "<!-- agentrepocoach -->" in output

    def test_coaching_tips_included(self) -> None:
        tips = [
            {
                "component": "error_quality",
                "label": "Low fix-hint coverage",
                "tip": "Add fix hints to error messages.",
            },
        ]
        output = format_pr_comment(self.comparison, coaching_tips=tips)
        assert "Top recommendations" in output
        assert "Low fix-hint coverage" in output
        assert "Add fix hints" in output

    def test_no_coaching_section_when_empty(self) -> None:
        output = format_pr_comment(self.comparison, coaching_tips=None)
        assert "Top recommendations" not in output

    def test_coaching_tips_limited_to_three(self) -> None:
        tips = [
            {"component": f"c{i}", "label": f"Tip {i}", "tip": f"Fix {i}"}
            for i in range(5)
        ]
        output = format_pr_comment(self.comparison, coaching_tips=tips)
        assert "Tip 0" in output
        assert "Tip 2" in output
        assert "Tip 3" not in output
