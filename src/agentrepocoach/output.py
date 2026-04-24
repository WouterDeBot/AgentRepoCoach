"""Output writers for AgentRepoCoach.

Three supported formats:

- JSON: full score breakdown, suitable for CI artifacts.
- Prometheus: exposition format for metric scraping.
- Markdown: short summary suitable for a PR comment.

Threat-model constraint: the JSON output must NEVER contain code snippets or
raw message bodies from scanned files — only counts, percentages, exception
type names, and file paths. The current component implementations already
honor this contract.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_METRIC_HELP = "AgentRepoCoach composite codebase agent health score (0-100)."
_METRIC_NAME = "agentrepocoach_codebase_health_score"


def render_json(result: dict[str, Any]) -> str:
    """Return the full score breakdown as a JSON string."""
    return json.dumps(result, indent=2, default=str)


def write_json(result: dict[str, Any], path: Path) -> None:
    """Write the full score breakdown as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(result) + "\n")


def render_prometheus(result: dict[str, Any]) -> str:
    """Return the score in Prometheus exposition format as a string."""
    lines = [
        f"# HELP {_METRIC_NAME} {_METRIC_HELP}",
        f"# TYPE {_METRIC_NAME} gauge",
        f'{_METRIC_NAME}{{component="total"}} {result["total"]}',
    ]
    for name, component in result.get("components", {}).items():
        score = component.get("score", 0)
        lines.append(f'{_METRIC_NAME}{{component="{name}"}} {score}')
    return "\n".join(lines)


def write_prometheus(result: dict[str, Any], path: Path) -> None:
    """Write the score in Prometheus exposition format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_prometheus(result) + "\n")


def render_markdown_comment(result: dict[str, Any]) -> str:
    """Return a short summary suitable for a GitHub PR comment as a string."""
    lines = [
        "### AgentRepoCoach — Codebase Agent Health",
        "",
        f"**Total score:** {result['total']:.2f} / 100",
        f"**Language:** `{result.get('language', 'unknown')}`",
        "",
        "| Component | Score | Weight |",
        "|---|---:|---:|",
    ]
    weights = result.get("weights", {})
    for name, component in result.get("components", {}).items():
        weight = weights.get(name, 0.0)
        lines.append(f"| {name} | {component['score']:.2f} / 100 | {weight:.2f} |")
    tips = generate_coaching(result)
    coaching = format_coaching_markdown(tips)
    if coaching:
        lines.append(coaching)
    lines.append("<!-- agentrepocoach -->")
    return "\n".join(lines)


def write_markdown_comment(result: dict[str, Any], path: Path) -> None:
    """Write a short summary suitable for a GitHub PR comment."""
    lines = [
        "### AgentRepoCoach — Codebase Agent Health",
        "",
        f"**Total score:** {result['total']:.2f} / 100",
        f"**Language:** `{result.get('language', 'unknown')}`",
        "",
        "| Component | Score | Weight |",
        "|---|---:|---:|",
    ]
    weights = result.get("weights", {})
    for name, component in result.get("components", {}).items():
        weight = weights.get(name, 0.0)
        lines.append(f"| {name} | {component['score']:.2f} / 100 | {weight:.2f} |")
    tips = generate_coaching(result)
    coaching = format_coaching_markdown(tips)
    if coaching:
        lines.append(coaching)
    lines.append("<!-- agentrepocoach -->")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Coaching recommendations engine
# ---------------------------------------------------------------------------

# Maps (component, sub_component) to (short label, actionable fix suggestion).
# Only sub-components with known coaching text are included.
_COACHING_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("navigability", "agents_md"): (
        "Missing AGENTS.md",
        "Create an AGENTS.md at the repo root that links to your codebase map, "
        "CLI manifest, and ADR directory. This is the first file AI agents read.",
    ),
    ("navigability", "codebase_map"): (
        "Incomplete codebase map",
        "Create or update docs/codebase-map.md to list every production module "
        "with a one-line description of what it does.",
    ),
    ("navigability", "cli_manifest"): (
        "Missing or stale CLI manifest",
        "Create docs/cli-manifest.json listing your CLI commands and their flags. "
        "Keep it fresh — agents use it to discover available operations.",
    ),
    ("navigability", "root_cleanliness"): (
        "Root directory clutter",
        "Remove stale artifacts (backup files, old reports) from the repo root. "
        "A clean root helps agents orient faster.",
    ),
    ("error_quality", "hint_coverage"): (
        "Low fix-hint coverage in errors",
        "Add actionable fix hints to your error messages (e.g., 'Try ...', "
        "'See docs/...', 'Did you mean ...'). Agents recover faster from errors "
        "that explain what to do next.",
    ),
    ("error_quality", "exception_subclass_ratio"): (
        "Too few domain-specific error types",
        "Replace generic exceptions with domain-specific subtypes. Agents can "
        "handle a ValidationError differently from a ConnectionError — but only "
        "if you distinguish them in your type hierarchy.",
    ),
    ("error_quality", "generic_exception_dominance"): (
        "Generic exceptions dominate",
        "Reduce use of bare Exception/Error throws. Wrap them in domain types "
        "so agents can match on specific error categories.",
    ),
    ("decision_queryability", "adr_catalog"): (
        "Few or no ADRs",
        "Create Architecture Decision Records in docs/adr/ (e.g., ADR-001-*.md). "
        "Agents consult ADRs to understand why the codebase is shaped the way it is.",
    ),
    ("decision_queryability", "inline_ref_resolution"): (
        "Missing inline ADR references",
        "Add ADR-NNN references in code comments near decisions. This lets agents "
        "trace from code back to the rationale without searching.",
    ),
    ("test_quality", "naming_convention"): (
        "Test names lack structure",
        "Use descriptive test names that encode the scenario and expectation "
        "(e.g., test_doWork_negativeInput_returnsError). Agents use test names "
        "to understand intended behavior.",
    ),
    ("test_quality", "helper_files"): (
        "No test helpers or builders",
        "Add shared test helpers (builders, factories) to reduce fixture duplication "
        "and make test setup readable for agents.",
    ),
    ("test_quality", "fixture_duplication"): (
        "Fixture code is duplicated across tests",
        "Extract shared test fixtures into conftest/setUp helpers. Duplicated setup "
        "wastes agent context and increases mutation surface.",
    ),
    ("module_hygiene", "internal_visibility"): (
        "Low internal visibility usage",
        "Mark implementation-detail types as internal/private. Public-by-default "
        "forces agents to consider your entire surface area as API.",
    ),
    ("module_hygiene", "god_files"): (
        "God files detected",
        "Split files over 500 lines into focused modules. Large files overflow "
        "agent context windows and slow down navigation.",
    ),
    ("module_hygiene", "doc_comment_coverage"): (
        "Low doc comment coverage",
        "Add doc comments (JSDoc, docstrings, XML docs, /// comments) to public "
        "declarations. Agents read these before reading function bodies.",
    ),
    ("module_hygiene", "architecture_doc"): (
        "Missing or stale architecture doc",
        "Create or update docs/architecture.md with a high-level overview of your "
        "system's modules and data flow.",
    ),
}


def generate_coaching(result: dict[str, Any], max_tips: int = 3) -> list[dict[str, Any]]:
    """Return the top coaching recommendations sorted by impact (biggest gap first).

    Each recommendation is a dict with: component, sub_component, label, tip,
    current_score, max_score, gap.
    """
    gaps: list[dict[str, Any]] = []
    for comp_name, component in result.get("components", {}).items():
        weight = result.get("weights", {}).get(comp_name, 0.0)
        for sub_name, sub in component.get("breakdown", {}).items():
            score = sub.get("score", 0)
            maximum = sub.get("max", 0)
            if maximum <= 0:
                continue
            gap = maximum - score
            if gap <= 0:
                continue
            key = (comp_name, sub_name)
            if key not in _COACHING_MAP:
                continue
            label, tip = _COACHING_MAP[key]
            # Weighted gap: how much this sub-component could improve the total.
            weighted_gap = gap * weight
            gaps.append({
                "component": comp_name,
                "sub_component": sub_name,
                "label": label,
                "tip": tip,
                "current_score": score,
                "max_score": maximum,
                "gap": gap,
                "weighted_gap": weighted_gap,
            })
    gaps.sort(key=lambda g: g["weighted_gap"], reverse=True)
    return gaps[:max_tips]


def format_coaching(tips: list[dict[str, Any]]) -> str:
    """Format coaching tips for terminal output."""
    if not tips:
        return ""
    lines = ["", "Top recommendations to improve your score:", ""]
    for i, tip in enumerate(tips, 1):
        lines.append(
            f"  {i}. [{tip['component']}] {tip['label']} "
            f"({tip['current_score']:.0f}/{tip['max_score']:.0f} pts)"
        )
        lines.append(f"     {tip['tip']}")
        lines.append("")
    return "\n".join(lines)


def format_coaching_markdown(tips: list[dict[str, Any]]) -> str:
    """Format coaching tips as markdown."""
    if not tips:
        return ""
    lines = [
        "",
        "#### Top recommendations",
        "",
    ]
    for i, tip in enumerate(tips, 1):
        lines.append(
            f"{i}. **{tip['label']}** "
            f"(`{tip['component']}` — {tip['current_score']:.0f}/{tip['max_score']:.0f} pts)"
        )
        lines.append(f"   {tip['tip']}")
        lines.append("")
    return "\n".join(lines)


def format_summary(result: dict[str, Any]) -> str:
    """Return a terminal-friendly summary with coaching tips."""
    lines = [
        "AgentRepoCoach — Codebase Agent Health",
        "=================================",
        f"Total score:   {result['total']:.2f} / 100",
        f"Language:      {result.get('language', 'unknown')}",
        "",
        "Components:",
    ]
    weights = result.get("weights", {})
    for name, component in result.get("components", {}).items():
        weight = weights.get(name, 0.0)
        contribution = weight * component["score"]
        lines.append(
            f"  {name:25s} {component['score']:6.2f} / 100   "
            f"weight={weight:.2f}   contribution={contribution:6.2f}"
        )
    tips = generate_coaching(result)
    coaching = format_coaching(tips)
    if coaching:
        lines.append(coaching)
    return "\n".join(lines)


def format_comparison(current: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Return a terminal-friendly delta table comparing *current* against *baseline*."""
    cur_total = current["total"]
    base_total = baseline["total"]
    delta_total = cur_total - base_total

    lines = [
        "AgentRepoCoach — Score Comparison",
        "=================================",
        f"Total: {base_total:.2f} -> {cur_total:.2f} ({delta_total:+.2f})",
        "",
        f"  {'Component':25s} {'Baseline':>10s} {'Current':>10s} {'Delta':>10s}",
        f"  {'-' * 25} {'-' * 10} {'-' * 10} {'-' * 10}",
    ]

    base_components = baseline.get("components", {})
    cur_components = current.get("components", {})
    all_names = list(dict.fromkeys(list(base_components) + list(cur_components)))

    for name in all_names:
        base_score = base_components.get(name, {}).get("score", 0.0)
        cur_score = cur_components.get(name, {}).get("score", 0.0)
        delta = cur_score - base_score
        lines.append(
            f"  {name:25s} {base_score:10.2f} {cur_score:10.2f} {delta:+10.2f}"
        )

    return "\n".join(lines)


def format_comparison_markdown(current: dict[str, Any], baseline: dict[str, Any]) -> str:
    """Return a markdown delta table suitable for a GitHub PR comment."""
    cur_total = current["total"]
    base_total = baseline["total"]
    delta_total = cur_total - base_total

    lines = [
        "### AgentRepoCoach — Score Comparison",
        "",
        f"**Total score:** {base_total:.2f} -> {cur_total:.2f} ({delta_total:+.2f})",
        "",
        "| Component | Baseline | Current | Delta |",
        "|---|---:|---:|---:|",
    ]

    base_components = baseline.get("components", {})
    cur_components = current.get("components", {})
    all_names = list(dict.fromkeys(list(base_components) + list(cur_components)))

    for name in all_names:
        base_score = base_components.get(name, {}).get("score", 0.0)
        cur_score = cur_components.get(name, {}).get("score", 0.0)
        delta = cur_score - base_score
        lines.append(f"| {name} | {base_score:.2f} | {cur_score:.2f} | {delta:+.2f} |")

    # Append coaching tips from the current result
    tips = generate_coaching(current)
    coaching = format_coaching_markdown(tips)
    if coaching:
        lines.append(coaching)

    lines.append("<!-- agentrepocoach -->")

    return "\n".join(lines)


def format_verbose(result: dict[str, Any]) -> str:
    """Return the summary plus a per-sub-component breakdown."""
    lines = [format_summary(result), "", "Sub-component breakdown:"]
    for name, component in result.get("components", {}).items():
        lines.append(f"\n[{name}] {component['score']:.2f} / 100")
        for sub_name, sub in component.get("breakdown", {}).items():
            score = sub.get("score", 0)
            maximum = sub.get("max", 0)
            extras = {k: v for k, v in sub.items() if k not in {"score", "max"}}
            lines.append(f"  - {sub_name:30s} {score:6.2f} / {maximum:<3}   {extras}")
    return "\n".join(lines)
