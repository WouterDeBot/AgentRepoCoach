"""Bootstrap-signals component — scores the two artifacts an agent needs
to validate its own work against the repo: a runnable CI workflow on PRs
(50 pts), and a README that surfaces install + test commands in the
first 100 lines (50 pts).

Security invariants (AC-06):
- No subprocess, os.system, exec(), eval(), or __import__ calls.
- README reads are capped at _README_BYTE_CAP bytes before line scan.
- CI workflow scans are limited to _CI_FILES_MAX_SCAN files.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter
from ..config import BootstrapSignalsConfig, Config

_CI_SIGNAL_WEIGHT = 50
_README_QUALITY_WEIGHT = 50

_README_HEAD_LINES = 100        # line cap for README scoring
_README_BYTE_CAP = 200_000      # hard byte cap before line scan (DoS guard)
_CI_FILES_MAX_SCAN = 50         # short-circuit for pathological repos

# Regex patterns for detecting "on: pull_request" in YAML files.
# Covers three common forms:
#   on: pull_request
#   on: [pull_request, push]
#   on:\n  pull_request:
_PR_SCALAR_RE = re.compile(r"^on:\s+\[?[^#\n]*pull_request", re.MULTILINE)
_PR_MAP_BLOCK_RE = re.compile(r"^\s*on:\s*$", re.MULTILINE)
_PR_MAP_VALUE_RE = re.compile(r"^\s+pull_request\b", re.MULTILINE)


def compute_bootstrap_signals(
    repo_root: Path, config: Config, adapter: LanguageAdapter,
) -> dict[str, Any]:
    """Score the bootstrap-signals component.

    Returns a dict with ``{"score": float, "total": 100, "breakdown": {...}}``.
    The ``adapter`` parameter is accepted for interface consistency and future
    per-language override hooks; it is currently unused.
    """
    ci = _score_ci_signal(repo_root, config)
    readme = _score_readme_quality(repo_root, config)
    total = ci["score"] + readme["score"]
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {"ci_signal": ci, "readme_quality": readme},
    }


def _score_ci_signal(repo_root: Path, config: Config) -> dict[str, Any]:
    """Score CI-signal sub-component (0–50 pts).

    30 pts: any CI workflow file containing a recognisable test command exists.
    20 pts: at least one such workflow triggers on pull_request.
    """
    bsc = config.bootstrap_signals
    workflow_files: list[Path] = []
    for glob_pattern in bsc.ci_workflow_globs:
        matches = sorted(repo_root.glob(glob_pattern))
        workflow_files.extend(matches)
        if len(workflow_files) >= _CI_FILES_MAX_SCAN:
            workflow_files = workflow_files[:_CI_FILES_MAX_SCAN]
            break

    if not workflow_files:
        return {
            "score": 0,
            "total": _CI_SIGNAL_WEIGHT,
            "workflows_found": 0,
            "pr_trigger": False,
            "note": "No CI workflow files found.",
        }

    # 30 pts for having any workflow; 20 pts for a pull_request trigger.
    has_pr_trigger = any(_file_has_pr_trigger(f, config) for f in workflow_files)
    score = 30 + (20 if has_pr_trigger else 0)

    return {
        "score": score,
        "total": _CI_SIGNAL_WEIGHT,
        "workflows_found": len(workflow_files),
        "pr_trigger": has_pr_trigger,
    }


def _file_has_pr_trigger(path: Path, config: Config) -> bool:
    """Return True if the file triggers on pull_request."""
    try:
        byte_size = path.stat().st_size
        if byte_size > config.thresholds.max_file_bytes:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    # scalar form: on: pull_request  OR  on: [pull_request, push]
    if _PR_SCALAR_RE.search(text):
        return True

    # block map form: on:\n  pull_request:
    for match in _PR_MAP_BLOCK_RE.finditer(text):
        tail = text[match.end():]
        first_line = tail.lstrip("\n").split("\n")[0] if tail else ""
        if _PR_MAP_VALUE_RE.match("\n" + first_line):
            return True

    return False


def _score_readme_quality(repo_root: Path, config: Config) -> dict[str, Any]:
    """Score README-quality sub-component (0–50 pts).

    25 pts: a fenced code block in the first 100 lines contains an install command.
    25 pts: a fenced code block in the first 100 lines contains a test command.
    """
    bsc = config.bootstrap_signals

    # Try common README filenames in priority order.
    readme_path: Path | None = None
    for candidate in ("README.md", "README.rst", "README.txt", "README"):
        p = repo_root / candidate
        if p.is_file():
            readme_path = p
            break

    if readme_path is None:
        return {
            "score": 0,
            "total": _README_QUALITY_WEIGHT,
            "install_found": False,
            "test_found": False,
            "note": "No README file found.",
        }

    try:
        byte_size = readme_path.stat().st_size
        if byte_size > _README_BYTE_CAP:
            return {
                "score": 0,
                "total": _README_QUALITY_WEIGHT,
                "install_found": False,
                "test_found": False,
                "note": f"README exceeds {_README_BYTE_CAP} byte cap; skipped for DoS safety.",
            }
        text = readme_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "score": 0,
            "total": _README_QUALITY_WEIGHT,
            "install_found": False,
            "test_found": False,
            "note": "README could not be read.",
        }

    head_lines = text.splitlines()[: bsc.readme_head_lines]
    code_blocks = _extract_fenced_code_blocks(head_lines)

    install_found = _any_matches(code_blocks, bsc.install_command_patterns)
    test_found = _any_matches(code_blocks, bsc.test_command_patterns)

    score = (25 if install_found else 0) + (25 if test_found else 0)
    return {
        "score": score,
        "total": _README_QUALITY_WEIGHT,
        "install_found": install_found,
        "test_found": test_found,
    }


def _extract_fenced_code_blocks(lines: list[str]) -> list[str]:
    """Return a flat list of all lines that appear inside fenced code blocks."""
    inside = False
    fence_marker = ""
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not inside:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                inside = True
                fence_marker = stripped[:3]
        else:
            if stripped.startswith(fence_marker) and len(stripped) >= len(fence_marker):
                inside = False
                fence_marker = ""
            else:
                collected.append(line)

    return collected


def _any_matches(lines: list[str], patterns: tuple[str, ...]) -> bool:
    """Return True if any line contains any of the pattern substrings."""
    for line in lines:
        for pattern in patterns:
            if pattern in line:
                return True
    return False
