"""Composite orchestrator — combines the 5 components into the CAH score."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters import LanguageAdapter, detect_all, detect_primary, get_adapter_by_name
from .components import (
    compute_bootstrap_signals,
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
        "bootstrap_signals": compute_bootstrap_signals(repo_root, config, adapter),
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


# Schema version for the multi-language output shape.
_MULTI_LANGUAGE_SCHEMA_VERSION = 2


def compute_cah_all(repo_root: Path, config: Config | None = None) -> dict[str, Any]:
    """Compute CAH scores for every language that meets the detection threshold.

    Uses ``detect_all()`` to find adapters with ``confidence >= 0.5`` AND
    ``file_count >= 3``, then calls ``compute_cah()`` once per adapter.

    The returned dict uses a nested shape distinct from the single-language
    shape so downstream consumers can distinguish the two without ambiguity:

    .. code-block:: json

        {
            "schema_version": 2,
            "generator": "agentrepocoach <version>",
            "languages": {
                "python": {"total": 72.4, "components": {...}, "language": "python"},
                "typescript": {"total": 61.2, "components": {...}, "language": "typescript"}
            }
        }

    Note: the top-level ``"total"`` and ``"language"`` keys are intentionally
    **absent** — use the per-language sub-dicts for those values.

    Args:
        repo_root: Path to the repository to score.
        config: Optional explicit config. If None, loads from
            ``<repo_root>/.agentrepocoach.toml`` with defaults.

    Returns:
        Multi-language result dict as described above.  ``"languages"`` is
        empty when no adapter meets the threshold.
    """
    from . import VERSION  # local import to avoid circular reference

    repo_root = repo_root.resolve()
    if config is None:
        config = load_config(repo_root)

    adapters = detect_all(repo_root)

    per_language: dict[str, Any] = {}
    for _confidence, adapter in adapters:
        lang_result = compute_cah(repo_root, config=config, adapter=adapter)
        per_language[adapter.name] = lang_result

    return {
        "schema_version": _MULTI_LANGUAGE_SCHEMA_VERSION,
        "generator": f"{_GENERATOR_NAME} {VERSION}",
        "languages": per_language,
    }
