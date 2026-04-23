"""Composite orchestrator — combines the 5 components into the CAH score."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import LanguageAdapter, detect_primary, get_adapter_by_name
from .components import (
    compute_decision_queryability,
    compute_error_quality,
    compute_module_hygiene,
    compute_navigability,
    compute_test_quality,
)
from .config import Config, load_config

_GENERATOR_NAME = "agentrepocoach"


def compute_cah(repo_root: Path, config: Config | None = None, adapter: LanguageAdapter | None = None) -> dict[str, Any]:
    """Compute every component and assemble the weighted composite.

    Args:
        repo_root: Path to the repository to score.
        config: Optional explicit config. If None, loads from
            ``<repo_root>/.agentrepocoach.toml`` with defaults.
        adapter: Optional explicit language adapter. If None, auto-detects.

    Returns:
        A dict with ``schema_version``, ``generator``, ``total``, ``weights``,
        ``components``, and ``language``.
    """
    from . import VERSION  # local import to avoid circular reference

    repo_root = repo_root.resolve()
    if config is None:
        config = load_config(repo_root)
    if adapter is None:
        adapter = _pick_adapter(repo_root, config)

    components = {
        "navigability": compute_navigability(repo_root, config, adapter),
        "error_quality": compute_error_quality(repo_root, config, adapter),
        "decision_queryability": compute_decision_queryability(repo_root, config, adapter),
        "test_quality": compute_test_quality(repo_root, config, adapter),
        "module_hygiene": compute_module_hygiene(repo_root, config, adapter),
    }

    total = 0.0
    for name, weight in config.weights.items():
        total += weight * components[name]["score"]

    result = {
        "schema_version": config.schema_version,
        "generator": f"{_GENERATOR_NAME} {VERSION}",
        "total": round(total, 2),
        "weights": dict(config.weights),
        "language": adapter.name,
        "components": components,
    }

    # Generate coaching recommendations from the scored result.
    from .output import generate_coaching
    tips = generate_coaching(result)
    if tips:
        result["coaching"] = [
            {
                "component": t["component"],
                "sub_component": t["sub_component"],
                "label": t["label"],
                "tip": t["tip"],
                "gap": round(t["gap"], 2),
            }
            for t in tips
        ]

    return result


def _pick_adapter(repo_root: Path, config: Config) -> LanguageAdapter:
    """Pick the adapter either by explicit config or auto-detection."""
    if config.language and config.language != "auto":
        return get_adapter_by_name(config.language)
    return detect_primary(repo_root)
