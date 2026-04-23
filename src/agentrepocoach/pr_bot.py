"""PR comparison and commenting utilities for CI integration.

Provides structured score comparison, markdown formatting with delta
indicators, and JSON output parsing -- designed for use in GitHub Actions
workflows that post CAH score comparisons as PR comments.

Complements ``output.py`` which provides raw formatting functions.  This
module adds higher-level semantics (improved/regressed classification,
arrow indicators, coaching-tip integration) suitable for bot-generated
PR comments.
"""
from __future__ import annotations

import json
from typing import Any


def parse_score_output(json_str: str) -> dict[str, Any]:
    """Parse the JSON output from the AgentRepoCoach CLI.

    Parameters
    ----------
    json_str:
        Raw JSON string produced by ``agentrepocoach --format json``.

    Returns
    -------
    dict with ``total`` (float), ``language`` (str), ``components`` (dict
    mapping component name to its score dict), and ``weights`` (dict).

    Raises
    ------
    ValueError
        If *json_str* is not valid JSON or lacks the ``total`` key.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if "total" not in data:
        raise ValueError("JSON output missing required 'total' key")

    return data


def compare_scores(base_scores: dict, pr_scores: dict) -> dict[str, Any]:
    """Compute deltas between base-branch and PR-branch scores.

    Parameters
    ----------
    base_scores:
        Score dict for the base (target) branch.
    pr_scores:
        Score dict for the PR (source) branch.

    Returns
    -------
    dict with keys:
        - ``base_total`` (float)
        - ``pr_total`` (float)
        - ``delta`` (float) -- pr_total - base_total
        - ``component_deltas`` -- list of dicts, each with ``name``,
          ``base_score``, ``pr_score``, ``delta``
        - ``improved`` -- list of component names where score increased
        - ``regressed`` -- list of component names where score decreased
    """
    base_total = float(base_scores.get("total", 0))
    pr_total = float(pr_scores.get("total", 0))
    delta = pr_total - base_total

    base_components = base_scores.get("components", {})
    pr_components = pr_scores.get("components", {})
    all_names = list(dict.fromkeys(list(base_components) + list(pr_components)))

    component_deltas: list[dict[str, Any]] = []
    improved: list[str] = []
    regressed: list[str] = []

    for name in all_names:
        base_score = float(base_components.get(name, {}).get("score", 0.0))
        pr_score = float(pr_components.get(name, {}).get("score", 0.0))
        comp_delta = pr_score - base_score

        component_deltas.append({
            "name": name,
            "base_score": base_score,
            "pr_score": pr_score,
            "delta": comp_delta,
        })

        if comp_delta > 0:
            improved.append(name)
        elif comp_delta < 0:
            regressed.append(name)

    return {
        "base_total": base_total,
        "pr_total": pr_total,
        "delta": delta,
        "component_deltas": component_deltas,
        "improved": improved,
        "regressed": regressed,
    }


def _delta_indicator(delta: float) -> str:
    """Return an arrow indicator for a delta value."""
    if delta > 0:
        return "^"
    if delta < 0:
        return "v"
    return "="


def format_pr_comment(
    comparison: dict[str, Any],
    coaching_tips: list[dict[str, Any]] | None = None,
) -> str:
    """Format a score comparison as a GitHub PR comment in markdown.

    Parameters
    ----------
    comparison:
        Dict returned by :func:`compare_scores`.
    coaching_tips:
        Optional list of coaching tip dicts (as returned by
        ``output.generate_coaching``).  Each must have at least
        ``label``, ``component``, and ``tip`` keys.

    Returns
    -------
    Markdown string ready to post as a GitHub PR comment.  Contains the
    ``<!-- agentrepocoach -->`` marker for idempotent comment updates.
    """
    base_total = comparison["base_total"]
    pr_total = comparison["pr_total"]
    delta = comparison["delta"]
    total_indicator = _delta_indicator(delta)

    lines = [
        "### AgentRepoCoach -- Score Comparison",
        "",
        f"**Total:** {base_total:.2f} -> {pr_total:.2f} "
        f"({delta:+.2f}) {total_indicator}",
        "",
        "| Component | Base | PR | Delta | |",
        "|---|---:|---:|---:|:---:|",
    ]

    for comp in comparison.get("component_deltas", []):
        indicator = _delta_indicator(comp["delta"])
        lines.append(
            f"| {comp['name']} "
            f"| {comp['base_score']:.2f} "
            f"| {comp['pr_score']:.2f} "
            f"| {comp['delta']:+.2f} "
            f"| {indicator} |"
        )

    if coaching_tips:
        lines.append("")
        lines.append("#### Top recommendations")
        lines.append("")
        for i, tip in enumerate(coaching_tips[:3], 1):
            lines.append(
                f"{i}. **{tip['label']}** "
                f"(`{tip['component']}`) -- {tip['tip']}"
            )

    lines.append("")
    lines.append("<!-- agentrepocoach -->")

    return "\n".join(lines)
