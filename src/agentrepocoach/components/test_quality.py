"""Test quality component.

Scores test readability and fixture hygiene — not test coverage. Coverage is
a solved problem (codecov etc.); this component measures whether the test
suite tells an agent what each test does without running it.

- 40 pts: % of test methods that match the idiomatic naming convention.
- 30 pts: enough reusable helper files to discourage copy-paste fixtures.
- 30 pts: configured fixture-duplication patterns appear sparingly.

``fixture_duplication_patterns`` is empty by default — the sub-score gives
full credit unless the user opts in by listing project-specific patterns.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter
from ..adapters.base import iter_source_files
from ..config import Config
from ..scoring import scale_linear

_NAMING_WEIGHT = 40
_HELPERS_WEIGHT = 30
_DUPLICATION_WEIGHT = 30
_DUP_FULL_MAX = 50
_DUP_ZERO_MAX = 200


def compute_test_quality(repo_root: Path, config: Config, adapter: LanguageAdapter) -> dict[str, Any]:
    """Score test naming convention + helper count + fixture duplication."""
    test_files = adapter.find_test_files(repo_root)

    naming = _score_test_naming(test_files, adapter)
    helpers = _score_test_helpers(repo_root, config, test_files)
    duplication = _score_fixture_duplication(test_files, config)

    total = naming["score"] + helpers["score"] + duplication["score"]
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {
            "naming_convention": naming,
            "helper_files": helpers,
            "fixture_duplication": duplication,
        },
    }


def _score_test_naming(
    test_files: list[Path],
    adapter: LanguageAdapter,
) -> dict[str, Any]:
    """40 pts: % of test methods matching the adapter's naming convention."""
    methods = adapter.find_test_methods(test_files)
    pattern = adapter.test_naming_pattern()

    total = len(methods)
    if total == 0:
        return {
            "score": 0,
            "max": _NAMING_WEIGHT,
            "total_methods": 0,
            "matching_methods": 0,
            "pct": 0.0,
        }

    matching = sum(1 for _, name in methods if pattern.match(name))
    pct = 100.0 * matching / total
    score = scale_linear(pct, zero_at=0.0, full_at=100.0, max_pts=_NAMING_WEIGHT)
    return {
        "score": round(score, 2),
        "max": _NAMING_WEIGHT,
        "total_methods": total,
        "matching_methods": matching,
        "pct": round(pct, 2),
    }


def _score_test_helpers(
    repo_root: Path,
    config: Config,
    test_files: list[Path],
) -> dict[str, Any]:
    """30 pts: count of helper files under the configured helpers directory."""
    helpers_dir = _resolve_helpers_dir(repo_root, config, test_files)
    if helpers_dir is None or not helpers_dir.is_dir():
        return {"score": 0, "max": _HELPERS_WEIGHT, "helper_count": 0}

    # Count helpers using a neutral suffix list: any source file under the
    # helpers dir. The active adapter's production-file suffix set is a fair
    # proxy; we reuse iter_source_files to respect symlink/size guards.
    helpers = iter_source_files(
        helpers_dir,
        suffixes=(".cs", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go"),
    )
    count = len(helpers)
    score = scale_linear(
        count,
        zero_at=0,
        full_at=config.test_quality.helpers_full_count,
        max_pts=_HELPERS_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _HELPERS_WEIGHT,
        "helper_count": count,
    }


def _resolve_helpers_dir(
    repo_root: Path,
    config: Config,
    test_files: list[Path],
) -> Path | None:
    """Resolve the helpers directory from config ('auto' means guess)."""
    configured = config.paths.test_helpers_dir
    if configured and configured != "auto":
        return repo_root / configured

    # Auto-discovery: look for a TestHelpers / fixtures / helpers directory
    # under any test file's parent chain.
    candidates = ("TestHelpers", "test_helpers", "helpers", "fixtures", "conftest")
    seen: set[Path] = set()
    for test_file in test_files:
        for parent in test_file.parents:
            if parent == repo_root or parent == repo_root.parent:
                break
            for name in candidates:
                candidate = parent / name
                if candidate.is_dir() and candidate not in seen:
                    seen.add(candidate)
                    return candidate
    return None


def _score_fixture_duplication(
    test_files: list[Path],
    config: Config,
) -> dict[str, Any]:
    """30 pts: configured fixture-duplication patterns are rare."""
    patterns = config.test_quality.fixture_duplication_patterns
    if not patterns:
        return {
            "score": _DUPLICATION_WEIGHT,
            "max": _DUPLICATION_WEIGHT,
            "duplicate_builder_count": 0,
            "note": "no fixture_duplication_patterns configured",
        }

    compiled: list[re.Pattern[str]] = []
    for raw in patterns:
        try:
            compiled.append(re.compile(raw))
        except re.error:
            continue

    total = 0
    for path in test_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in compiled:
            total += len(pattern.findall(text))

    score = scale_linear(
        total,
        zero_at=_DUP_ZERO_MAX,
        full_at=_DUP_FULL_MAX,
        max_pts=_DUPLICATION_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _DUPLICATION_WEIGHT,
        "duplicate_builder_count": total,
    }
