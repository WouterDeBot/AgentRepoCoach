"""Module hygiene component.

Scores how neatly a codebase's production modules are organized:

- 30 pts: enough files declare internal / non-public types (visibility hygiene).
- 30 pts: god files (files over a size threshold) are rare.
- 20 pts: public declarations have doc comments.
- 20 pts: architecture doc is fresh.

Every file scan goes through the active language adapter — the component
never looks at file suffixes directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter
from ..adapters.base import count_file_loc
from ..config import Config
from ..scoring import file_mtime_age_days, scale_linear

_INTERNAL_WEIGHT = 30
_GOD_FILE_WEIGHT = 30
_DOC_COMMENT_WEIGHT = 20
_ARCH_WEIGHT = 20
_GOD_FILE_FULL_COUNT = 5
_GOD_FILE_ZERO_COUNT = 15


def compute_module_hygiene(repo_root: Path, config: Config, adapter: LanguageAdapter) -> dict[str, Any]:
    """Score internal visibility + god files + doc coverage + arch doc freshness."""
    production_files = adapter.find_production_files(repo_root)
    declarations = adapter.scan_declarations(production_files)

    internal = _score_internal_visibility(declarations, production_files, config)
    god = _score_god_files(production_files, config)
    docs = _score_doc_coverage(declarations, config)
    arch = _score_architecture_doc(repo_root, config)

    total = internal["score"] + god["score"] + docs["score"] + arch["score"]
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {
            "internal_visibility": internal,
            "god_files": god,
            "doc_comment_coverage": docs,
            "architecture_doc": arch,
        },
    }


def _score_internal_visibility(
    declarations: list[Any],
    production_files: list[Path],
    config: Config,
) -> dict[str, Any]:
    """30 pts: proportion of production files that declare a non-public type."""
    if not production_files:
        return {
            "score": 0,
            "max": _INTERNAL_WEIGHT,
            "internal_files": 0,
            "total_files": 0,
            "ratio": 0.0,
        }
    files_with_internal: set[Path] = set()
    for decl in declarations:
        if decl.visibility in ("internal", "private"):
            files_with_internal.add(decl.file)
    ratio = len(files_with_internal) / len(production_files)
    score = scale_linear(
        ratio,
        zero_at=0.0,
        full_at=config.module_hygiene.internal_visibility_full_ratio,
        max_pts=_INTERNAL_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _INTERNAL_WEIGHT,
        "internal_files": len(files_with_internal),
        "total_files": len(production_files),
        "ratio": round(ratio, 3),
    }


def _score_god_files(production_files: list[Path], config: Config) -> dict[str, Any]:
    """30 pts: count of production files over the god-file LOC threshold."""
    threshold = config.thresholds.god_file_loc
    max_bytes = config.thresholds.max_file_bytes
    god: list[dict[str, Any]] = []
    for path in production_files:
        loc = count_file_loc(path, max_bytes=max_bytes)
        if loc > threshold:
            god.append({"path": str(path), "loc": loc})

    count = len(god)
    score = scale_linear(
        count,
        zero_at=_GOD_FILE_ZERO_COUNT,
        full_at=_GOD_FILE_FULL_COUNT,
        max_pts=_GOD_FILE_WEIGHT,
    )
    god.sort(key=lambda d: d["loc"], reverse=True)
    return {
        "score": round(score, 2),
        "max": _GOD_FILE_WEIGHT,
        "god_file_count": count,
        "top_5": [_relative_god_entry(d, production_files) for d in god[:5]],
    }


def _relative_god_entry(entry: dict[str, Any], production_files: list[Path]) -> dict[str, Any]:
    """Format a god-file entry with repo-relative path (no string splits)."""
    path = Path(entry["path"])
    # Find the closest common ancestor among production files (language-neutral).
    try:
        common = Path(*path.parts[:-1])
        rel = path.name if str(common) == "." else str(path)
    except (ValueError, IndexError):
        rel = str(path)
    return {"path": rel, "loc": entry["loc"]}


def _score_doc_coverage(declarations: list[Any], config: Config) -> dict[str, Any]:
    """20 pts: % of public declarations with a doc comment. Full at 90%."""
    public = [d for d in declarations if d.visibility == "public"]
    total = len(public)
    if total == 0:
        return {
            "score": _DOC_COMMENT_WEIGHT,
            "max": _DOC_COMMENT_WEIGHT,
            "total_public_declarations": 0,
            "documented": 0,
            "pct": 100.0,
        }
    documented = sum(1 for d in public if d.has_doc_comment)
    pct = 100.0 * documented / total
    score = scale_linear(
        pct,
        zero_at=0.0,
        full_at=config.thresholds.doc_comment_min_coverage_pct,
        max_pts=_DOC_COMMENT_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _DOC_COMMENT_WEIGHT,
        "total_public_declarations": total,
        "documented": documented,
        "pct": round(pct, 2),
    }


def _score_architecture_doc(repo_root: Path, config: Config) -> dict[str, Any]:
    """20 pts: architecture doc exists AND was touched recently."""
    path = repo_root / config.paths.architecture_doc
    if not path.is_file():
        return {"score": 0, "max": _ARCH_WEIGHT, "exists": False, "age_days": None}
    age = file_mtime_age_days(path)
    fresh_days = config.module_hygiene.architecture_doc_fresh_days
    if age <= fresh_days:
        return {
            "score": _ARCH_WEIGHT,
            "max": _ARCH_WEIGHT,
            "exists": True,
            "age_days": round(age, 2),
        }
    return {
        "score": _ARCH_WEIGHT / 2,
        "max": _ARCH_WEIGHT,
        "exists": True,
        "age_days": round(age, 2),
        "stale": True,
    }
