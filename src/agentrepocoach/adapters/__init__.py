"""Adapter registry and language detection."""
from __future__ import annotations

from pathlib import Path

from .base import Declaration, LanguageAdapter, NotSupportedError, ThrowSite
from .csharp import CSharpAdapter
from .go import GoAdapter
from .python import PythonAdapter
from .rust import RustAdapter
from .typescript import TypeScriptAdapter

_REGISTRY: dict[str, type[LanguageAdapter]] = {
    "csharp": CSharpAdapter,
    "python": PythonAdapter,
    "typescript": TypeScriptAdapter,
    "rust": RustAdapter,
    "go": GoAdapter,
}


class NoAdapterError(RuntimeError):
    """Raised when no adapter can handle the repository."""


def get_adapter_by_name(name: str) -> LanguageAdapter:
    """Instantiate an adapter by its registered name."""
    if name not in _REGISTRY:
        supported = ", ".join(sorted(_REGISTRY))
        msg = f"Unknown adapter '{name}'. Supported: {supported}."
        raise NoAdapterError(f"{msg} Check spelling or use --language to specify one of: {supported}.")
    return _REGISTRY[name]()


def _collect_candidates(repo_path: Path) -> list[tuple[float, LanguageAdapter]]:
    """Collect all adapters with confidence > 0.0, sorted descending by (confidence, file_count)."""
    candidates: list[tuple[float, LanguageAdapter]] = []
    for cls in _REGISTRY.values():
        adapter = cls()
        confidence = adapter.detect(repo_path)
        if confidence > 0.0:
            candidates.append((confidence, adapter))
    candidates.sort(
        key=lambda pair: (pair[0], len(pair[1].find_production_files(repo_path))),
        reverse=True,
    )
    return candidates


def detect_primary(repo_path: Path) -> LanguageAdapter:
    """Try every adapter and return the one with the highest detect() confidence.

    When multiple adapters tie on confidence, the adapter whose
    ``find_production_files`` returns more files wins — a repo with 20 .py
    files and a single .sln fixture is almost certainly a Python project.
    """
    candidates = _collect_candidates(repo_path)
    if not candidates:
        supported = ", ".join(sorted(_REGISTRY))
        msg = f"No supported language detected in {repo_path}. Supported: {supported}."
        raise NoAdapterError(f"{msg} Try using --language to force an adapter, or check that the repo contains a recognized project file.")
    return candidates[0][1]


def detect_all(repo_path: Path) -> list[tuple[float, LanguageAdapter]]:
    """Return all adapters that meet the detection threshold.

    An adapter is included when ``confidence >= 0.5`` AND it has
    ``file_count >= 3`` production files under ``repo_path``.  This filters
    out repos where a language appears only as tooling sprinkles (e.g. a
    single Makefile helper script in an otherwise Go repo).

    Returns:
        A list of ``(confidence, adapter)`` tuples, sorted descending by
        ``(confidence, file_count)``.  Returns an empty list when no adapter
        meets the threshold.
    """
    _CONFIDENCE_FLOOR = 0.5
    _FILE_COUNT_FLOOR = 3

    result: list[tuple[float, LanguageAdapter]] = []
    for confidence, adapter in _collect_candidates(repo_path):
        if confidence < _CONFIDENCE_FLOOR:
            continue
        if len(adapter.find_production_files(repo_path)) < _FILE_COUNT_FLOOR:
            continue
        result.append((confidence, adapter))
    return result


__all__ = [
    "CSharpAdapter",
    "Declaration",
    "GoAdapter",
    "LanguageAdapter",
    "NoAdapterError",
    "NotSupportedError",
    "PythonAdapter",
    "RustAdapter",
    "ThrowSite",
    "TypeScriptAdapter",
    "detect_all",
    "detect_primary",
    "get_adapter_by_name",
]
