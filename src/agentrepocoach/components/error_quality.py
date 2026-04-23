"""Error quality component.

Scores how actionable a repo's exceptions are for an AI agent. Agents fail
fastest on unactionable errors — a cryptic ``InvalidOperationException("bad
state")`` gives an agent nothing to work with.

- 50 pts: % of throw sites whose message contains an actionable fix hint.
- 30 pts: % of throws that use a user-defined (domain) exception subclass.
- 20 pts: language-stdlib generic exceptions do NOT dominate (bonus if rare).

All exception classification goes through the active language adapter.
Zero hard-coded exception type names in this file — every domain exception
name comes from config or adapter auto-discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter, ThrowSite
from ..config import Config
from ..scoring import scale_linear

_HINT_WEIGHT = 50
_SUBCLASS_WEIGHT = 30
_GENERIC_WEIGHT = 20
_HINT_FULL_PCT = 50.0
_SUBCLASS_FULL_RATIO = 0.50
_GENERIC_LOW_PCT = 20.0
_GENERIC_HIGH_PCT = 40.0


def compute_error_quality(repo_root: Path, config: Config, adapter: LanguageAdapter) -> dict[str, Any]:
    """Score error-message quality: hint coverage + exception typing."""
    production_files = adapter.find_production_files(repo_root)
    domain_types = _resolve_domain_exception_types(config, adapter, production_files)
    sites = adapter.scan_throw_sites(
        production_files,
        hint_marker=config.error_quality.hint_marker,
        domain_exception_types=domain_types,
    )

    hint = _score_hint_coverage(sites)
    subclass = _score_domain_subclass_ratio(sites)
    generic = _score_generic_dominance(sites, adapter.generic_exception_names())

    total = hint["score"] + subclass["score"] + generic["score"]
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {
            "hint_coverage": hint,
            "exception_subclass_ratio": subclass,
            "generic_exception_dominance": generic,
        },
    }


def _resolve_domain_exception_types(
    config: Config,
    adapter: LanguageAdapter,
    production_files: list[Path],
) -> set[str]:
    """Build the set of 'user-defined' exception type names.

    Priority:
    1. Explicit config ``error_quality.domain_exception_types`` list.
    2. Auto-discovery from the repo's own source (scan declarations whose
       name ends in 'Exception' or 'Error' — language-neutral heuristic).
    """
    explicit = set(config.error_quality.domain_exception_types)
    if explicit:
        return explicit

    # Auto-discover: scan declarations and keep any ending in Exception/Error.
    declarations = adapter.scan_declarations(production_files)
    discovered: set[str] = set()
    for decl in declarations:
        if decl.name.endswith("Exception") or decl.name.endswith("Error"):
            discovered.add(decl.name)
    return discovered


def _score_hint_coverage(sites: list[ThrowSite]) -> dict[str, Any]:
    """50 pts: % of throws with an actionable fix hint, scaled 0% -> 50%."""
    total = len(sites)
    if total == 0:
        return {
            "score": _HINT_WEIGHT,
            "max": _HINT_WEIGHT,
            "coverage_pct": 100.0,
            "total_sites": 0,
            "with_hint": 0,
            "note": "no throw sites",
        }
    with_hint = sum(1 for s in sites if s.has_fix_hint)
    pct = 100.0 * with_hint / total
    score = scale_linear(pct, zero_at=0.0, full_at=_HINT_FULL_PCT, max_pts=_HINT_WEIGHT)
    return {
        "score": round(score, 2),
        "max": _HINT_WEIGHT,
        "coverage_pct": round(pct, 2),
        "total_sites": total,
        "with_hint": with_hint,
    }


def _score_domain_subclass_ratio(sites: list[ThrowSite]) -> dict[str, Any]:
    """30 pts: % of throws using a user-defined (domain) exception class."""
    total = len(sites)
    if total == 0:
        return {
            "score": _SUBCLASS_WEIGHT,
            "max": _SUBCLASS_WEIGHT,
            "ratio": 1.0,
            "note": "no throw sites",
        }
    subclass_count = sum(1 for s in sites if s.is_user_defined)
    ratio = subclass_count / total
    score = scale_linear(
        ratio,
        zero_at=0.0,
        full_at=_SUBCLASS_FULL_RATIO,
        max_pts=_SUBCLASS_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _SUBCLASS_WEIGHT,
        "ratio": round(ratio, 3),
        "subclass_count": subclass_count,
        "total_throws": total,
    }


def _score_generic_dominance(
    sites: list[ThrowSite],
    generic_names: set[str],
) -> dict[str, Any]:
    """20 pts: generic stdlib exceptions should not dominate. Lower is better."""
    total = len(sites)
    if total == 0:
        return {
            "score": _GENERIC_WEIGHT,
            "max": _GENERIC_WEIGHT,
            "pct": 0.0,
            "note": "no throw sites",
        }
    generic_count = sum(1 for s in sites if s.exception_type in generic_names)
    pct = 100.0 * generic_count / total
    score = scale_linear(
        pct,
        zero_at=_GENERIC_HIGH_PCT,
        full_at=_GENERIC_LOW_PCT,
        max_pts=_GENERIC_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _GENERIC_WEIGHT,
        "pct": round(pct, 2),
        "generic_count": generic_count,
        "total_throws": total,
    }
