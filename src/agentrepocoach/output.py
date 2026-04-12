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


def write_json(result: dict[str, Any], path: Path) -> None:
    """Write the full score breakdown as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str) + "\n")


def write_prometheus(result: dict[str, Any], path: Path) -> None:
    """Write the score in Prometheus exposition format."""
    lines = [
        f"# HELP {_METRIC_NAME} {_METRIC_HELP}",
        f"# TYPE {_METRIC_NAME} gauge",
        f'{_METRIC_NAME}{{component="total"}} {result["total"]}',
    ]
    for name, component in result.get("components", {}).items():
        score = component.get("score", 0)
        lines.append(f'{_METRIC_NAME}{{component="{name}"}} {score}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


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
    lines.append("")
    lines.append("<!-- agentrepocoach -->")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def format_summary(result: dict[str, Any]) -> str:
    """Return a terminal-friendly summary."""
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
