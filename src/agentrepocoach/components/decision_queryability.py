"""Decision queryability component.

Scores how easily an AI agent can discover *why* the code is the way it is:

- 60 pts: ADR catalog has enough entries with valid frontmatter.
- 40 pts: inline references in source code resolve to an ADR body or filename.

The original research included a third sub-score (MCP tool availability)
worth 30 pts, but that sub-score required importing a proprietary internal
MCP server module at score-compute time. It has been **dropped** for the
public tool; the 30 pts were reallocated: adr_catalog 40 -> 60, and
inline_ref_resolution 30 -> 40. Total still sums to 100.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter
from ..config import Config
from ..scoring import scale_linear

_ADR_COUNT_WEIGHT = 60
_REF_RESOLVE_WEIGHT = 40
_REF_FULL_PCT = 90.0


def compute_decision_queryability(
    repo_root: Path,
    config: Config,
    adapter: LanguageAdapter,
) -> dict[str, Any]:
    """Score ADR catalog health + inline-ref resolution."""
    adr = _score_adr_catalog(repo_root, config)
    refs = _score_inline_ref_resolution(repo_root, config, adapter)

    total = adr["score"] + refs["score"]
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {
            "adr_catalog": adr,
            "inline_ref_resolution": refs,
        },
    }


def _score_adr_catalog(repo_root: Path, config: Config) -> dict[str, Any]:
    """60 pts: enough ADRs under the configured ADR dir, with valid frontmatter."""
    adr_dir = repo_root / config.paths.adr_dir
    if not adr_dir.is_dir():
        return {
            "score": 0,
            "max": _ADR_COUNT_WEIGHT,
            "count": 0,
            "valid_count": 0,
        }

    files = [p for p in sorted(adr_dir.glob("*.md")) if p.name.lower() != "readme.md"]
    valid = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _has_valid_frontmatter(text):
            valid += 1

    score = scale_linear(
        valid,
        zero_at=0,
        full_at=config.thresholds.adr_min_count,
        max_pts=_ADR_COUNT_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _ADR_COUNT_WEIGHT,
        "count": len(files),
        "valid_count": valid,
    }


def _has_valid_frontmatter(text: str) -> bool:
    """Return True if ``text`` begins with a --- fence and parses an id: key."""
    if not text.startswith("---"):
        return False
    lines = text.splitlines()
    if len(lines) < 2 or lines[0] != "---":
        return False
    for i in range(1, min(len(lines), 40)):
        if lines[i] == "---":
            break
        if lines[i].strip().lower().startswith("id:"):
            return True
    return False


def _score_inline_ref_resolution(
    repo_root: Path,
    config: Config,
    adapter: LanguageAdapter,
) -> dict[str, Any]:
    """40 pts: % of unique inline refs in production code that resolve to an ADR."""
    patterns = _compile_inline_ref_patterns(config.decision_queryability.inline_ref_patterns)
    if not patterns:
        return {
            "score": _REF_RESOLVE_WEIGHT,
            "max": _REF_RESOLVE_WEIGHT,
            "note": "no inline ref patterns configured",
        }

    production_files = adapter.find_production_files(repo_root)
    refs = _extract_refs(production_files, patterns)

    if not refs:
        return {
            "score": _REF_RESOLVE_WEIGHT,
            "max": _REF_RESOLVE_WEIGHT,
            "total_refs": 0,
            "resolved_refs": 0,
            "resolve_pct": 100.0,
            "note": "no inline refs found",
        }

    resolved, unresolved = _resolve_refs_against_adrs(refs, repo_root, config)
    pct = 100.0 * resolved / len(refs)
    score = scale_linear(pct, zero_at=0.0, full_at=_REF_FULL_PCT, max_pts=_REF_RESOLVE_WEIGHT)
    return {
        "score": round(score, 2),
        "max": _REF_RESOLVE_WEIGHT,
        "total_refs": len(refs),
        "resolved_refs": resolved,
        "resolve_pct": round(pct, 2),
        "unresolved_sample": unresolved[:10],
    }


def _compile_inline_ref_patterns(patterns: tuple[str, ...]) -> list[re.Pattern[str]]:
    """Compile config-provided pattern strings with word-boundary anchoring."""
    compiled: list[re.Pattern[str]] = []
    for raw in patterns:
        # Wrap in word boundaries if the user did not already supply them.
        anchored = raw if raw.startswith("\\b") else rf"\b{raw}\b"
        try:
            compiled.append(re.compile(anchored, re.IGNORECASE))
        except re.error:
            # Malformed regex -> skip silently; the user sees it in --verbose.
            continue
    return compiled


def _extract_refs(files: list[Path], patterns: list[re.Pattern[str]]) -> set[str]:
    refs: set[str] = set()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                token = re.sub(r"\s+", " ", match.group(0)).upper()
                refs.add(token)
    return refs


def _resolve_refs_against_adrs(
    refs: set[str],
    repo_root: Path,
    config: Config,
) -> tuple[int, list[str]]:
    adr_dir = repo_root / config.paths.adr_dir
    adr_bodies: list[str] = []
    adr_filenames: list[str] = []
    if adr_dir.is_dir():
        for path in adr_dir.glob("*.md"):
            if path.name.lower() == "readme.md":
                continue
            try:
                adr_bodies.append(path.read_text(encoding="utf-8", errors="ignore").lower())
                adr_filenames.append(path.name.lower())
            except OSError:
                continue

    resolved = 0
    unresolved: list[str] = []
    for ref in sorted(refs):
        needle = ref.lower()
        if any(needle in body for body in adr_bodies):
            resolved += 1
            continue
        if any(needle in name for name in adr_filenames):
            resolved += 1
            continue
        unresolved.append(ref)
    return resolved, unresolved
