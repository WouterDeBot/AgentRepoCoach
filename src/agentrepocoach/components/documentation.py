"""Navigability component ('documentation' file in the package).

Scores the agent navigability layer — the docs and entry points an AI agent
reads first when opening an unfamiliar repo:

- 30 pts: ``AGENTS.md`` exists and links to the codebase map, CLI manifest, and ADR dir.
- 30 pts: ``docs/codebase-map.md`` exists and mentions every production module.
- 20 pts: ``docs/cli-manifest.json`` exists, is fresh, and has enough commands.
- 20 pts: Root directory is free of stale artifacts.

All paths and thresholds are configurable via ``.agentrepocoach.toml``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..adapters import LanguageAdapter
from ..config import Config
from ..scoring import file_mtime_age_days, scale_linear

_AGENTS_MD_WEIGHT = 30
_CODEBASE_MAP_WEIGHT = 30
_CLI_MANIFEST_WEIGHT = 20
_ROOT_CLEAN_WEIGHT = 20

_STALE_ARTIFACT_PATTERNS = (
    re.compile(r".*\.json$"),
    re.compile(r".*-results\..*"),
    re.compile(r".*-backup\..*"),
    re.compile(r".*\.bak$"),
)


def compute_navigability(
    repo_root: Path,
    config: Config,
    adapter: LanguageAdapter,
) -> dict[str, Any]:
    """Score the agent navigability layer."""
    agents = _score_agents_md(repo_root, config)
    codebase_map = _score_codebase_map(repo_root, config, adapter)
    cli_manifest = _score_cli_manifest(repo_root, config)
    root_cleanliness = _score_root_cleanliness(repo_root, config)

    total = (
        agents["score"]
        + codebase_map["score"]
        + cli_manifest["score"]
        + root_cleanliness["score"]
    )
    return {
        "score": round(total, 2),
        "total": 100,
        "breakdown": {
            "agents_md": agents,
            "codebase_map": codebase_map,
            "cli_manifest": cli_manifest,
            "root_cleanliness": root_cleanliness,
        },
    }


def _score_agents_md(repo_root: Path, config: Config) -> dict[str, Any]:
    """30 pts: AGENTS.md exists AND links to map, manifest, and ADR dir."""
    path = repo_root / config.paths.agents_md
    required = [
        config.paths.codebase_map,
        config.paths.cli_manifest,
        config.paths.adr_dir.rstrip("/"),
    ]
    if not path.is_file():
        return {
            "score": 0,
            "max": _AGENTS_MD_WEIGHT,
            "exists": False,
            "missing_links": required,
        }

    text = path.read_text(encoding="utf-8", errors="ignore")
    missing = [link for link in required if link not in text]
    if missing:
        partial = 10 + (len(required) - len(missing)) / len(required) * 20
        return {
            "score": round(partial, 2),
            "max": _AGENTS_MD_WEIGHT,
            "exists": True,
            "missing_links": missing,
        }
    return {
        "score": _AGENTS_MD_WEIGHT,
        "max": _AGENTS_MD_WEIGHT,
        "exists": True,
        "missing_links": [],
    }


def _score_codebase_map(
    repo_root: Path,
    config: Config,
    adapter: LanguageAdapter,
) -> dict[str, Any]:
    """30 pts: codebase map exists AND mentions every production module."""
    path = repo_root / config.paths.codebase_map
    required_modules = adapter.find_production_modules(repo_root)
    total_modules = len(required_modules)

    if not path.is_file():
        return {
            "score": 0,
            "max": _CODEBASE_MAP_WEIGHT,
            "exists": False,
            "matched_projects": 0,
            "total_projects": total_modules,
        }
    if total_modules == 0:
        # Nothing to check -> give full credit, noting the adapter found no
        # modules (which the module_hygiene component will also reflect).
        return {
            "score": _CODEBASE_MAP_WEIGHT,
            "max": _CODEBASE_MAP_WEIGHT,
            "exists": True,
            "matched_projects": 0,
            "total_projects": 0,
            "note": "no production modules discovered",
        }

    text = path.read_text(encoding="utf-8", errors="ignore")
    matched = sum(1 for name in required_modules if name in text)
    ratio = matched / total_modules
    score = round(ratio * _CODEBASE_MAP_WEIGHT, 2)
    return {
        "score": score,
        "max": _CODEBASE_MAP_WEIGHT,
        "exists": True,
        "matched_projects": matched,
        "total_projects": total_modules,
    }


def _score_cli_manifest(repo_root: Path, config: Config) -> dict[str, Any]:
    """20 pts: manifest exists, is fresh, and has enough commands."""
    path = repo_root / config.paths.cli_manifest
    if not path.is_file():
        return {"score": 0, "max": _CLI_MANIFEST_WEIGHT, "exists": False}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "score": 0,
            "max": _CLI_MANIFEST_WEIGHT,
            "exists": True,
            "parse_error": str(exc),
        }

    command_count = len(data.get("commands", []) or [])
    age_days = file_mtime_age_days(path)

    thresholds = config.thresholds
    if age_days <= thresholds.cli_manifest_fresh_days:
        freshness_pts = float(_CLI_MANIFEST_WEIGHT)
    elif age_days <= thresholds.cli_manifest_stale_days:
        freshness_pts = _CLI_MANIFEST_WEIGHT / 2.0
    else:
        freshness_pts = 0.0

    if command_count < thresholds.cli_manifest_min_commands:
        freshness_pts /= 2.0

    return {
        "score": round(freshness_pts, 2),
        "max": _CLI_MANIFEST_WEIGHT,
        "exists": True,
        "age_days": round(age_days, 2),
        "command_count": command_count,
    }


def _score_root_cleanliness(repo_root: Path, config: Config) -> dict[str, Any]:
    """20 pts: no stale artifacts in the repo root."""
    allowlist = set(config.root_allowlist)
    violations: list[str] = []
    for entry in sorted(repo_root.iterdir()):
        if entry.is_dir():
            continue
        name = entry.name
        if name in allowlist:
            continue
        for pattern in _STALE_ARTIFACT_PATTERNS:
            if pattern.match(name):
                violations.append(name)
                break

    count = len(violations)
    score = scale_linear(
        count,
        zero_at=config.thresholds.root_stale_max_penalty_count,
        full_at=0,
        max_pts=_ROOT_CLEAN_WEIGHT,
    )
    return {
        "score": round(score, 2),
        "max": _ROOT_CLEAN_WEIGHT,
        "violation_count": count,
        "violations": violations[:10],
    }
