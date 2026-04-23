"""Language adapter abstract base class.

Every supported language contributes one concrete adapter subclass with a
single-file footprint. The base class declares the 9 methods components need
to compute the Codebase Agent Health (CAH) score.

Adapters are language-neutral contracts. No component should contain a
language-specific regex or file-extension check; that belongs here.
"""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ThrowSite:
    """A language-neutral throw/raise site descriptor."""
    file: Path
    line: int
    exception_type: str
    has_fix_hint: bool
    is_user_defined: bool
    is_generic: bool


@dataclass(frozen=True)
class Declaration:
    """A top-level declaration (class/struct/function) with visibility info."""
    file: Path
    line: int
    name: str
    visibility: str  # "public" | "internal" | "private"
    has_doc_comment: bool


class NotSupportedError(NotImplementedError):
    """Raised by stub adapters that detect the language but cannot analyze it."""


class LanguageAdapter(ABC):
    """Abstract language adapter. One concrete implementation per language."""

    name: str = "base"

    # ------- Detection -------

    @abstractmethod
    def detect(self, repo_path: Path) -> float:
        """Return a 0.0-1.0 confidence score that this adapter applies."""

    # ------- File discovery -------

    @abstractmethod
    def find_production_files(self, repo_path: Path) -> list[Path]:
        """All source files for production modules, filtered for generated/build artifacts."""

    @abstractmethod
    def find_test_files(self, repo_path: Path) -> list[Path]:
        """All source files under the repo's test directory convention."""

    @abstractmethod
    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Logical module names (projects/packages) used by navigability's codebase_map check."""

    # ------- Throw-site analysis (error_quality) -------

    @abstractmethod
    def scan_throw_sites(
        self,
        files: Iterable[Path],
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        """Find every throw/raise and classify it."""

    @abstractmethod
    def generic_exception_names(self) -> set[str]:
        """Language-stdlib exception types considered 'too generic'."""

    # ------- Declarations (module_hygiene) -------

    @abstractmethod
    def scan_declarations(self, files: Iterable[Path]) -> list[Declaration]:
        """Find every top-level declaration with visibility and doc-comment flag."""

    # ------- Test-method analysis (test_quality) -------

    @abstractmethod
    def find_test_methods(self, files: Iterable[Path]) -> list[tuple[Path, str]]:
        """Return list of (file, method_name) for every test method."""

    @abstractmethod
    def test_naming_pattern(self) -> re.Pattern[str]:
        """Regex matching the idiomatic test-method naming convention."""


# ---------------------------------------------------------------------------
# Safe file iteration helpers — shared by all adapters.
# ---------------------------------------------------------------------------


def iter_source_files(root: Path, suffixes: tuple[str, ...], exclude_substrings: tuple[str, ...] = (), exclude_suffixes: tuple[str, ...] = (), follow_symlinks: bool = False, max_file_bytes: int = 10_485_760) -> list[Path]:
    """Walk ``root`` and return files matching ``suffixes``.

    Hardened against three threat-model risks:

    1. Symlink traversal — ``follow_symlinks=False`` by default.
    2. Large-file OOM — files over ``max_file_bytes`` are skipped.
    3. Path injection via resolved-outside-root — only entries under ``root``
       after ``os.walk`` are returned.
    """
    results: list[Path] = []
    if not root.is_dir():
        return results
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        # Prune excluded directories in-place so os.walk does not descend.
        dirnames[:] = [d for d in dirnames if not _is_excluded_segment(d)]
        for filename in filenames:
            if not any(filename.endswith(sfx) for sfx in suffixes):
                continue
            if exclude_suffixes and any(filename.endswith(sfx) for sfx in exclude_suffixes):
                continue
            path_str = os.path.join(dirpath, filename)
            if exclude_substrings and any(needle in path_str for needle in exclude_substrings):
                continue
            path = Path(path_str)
            if not follow_symlinks and path.is_symlink():
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            results.append(path)
    return results


# Default directories to prune during iteration. Covers common build / cache
# directories across all languages.
_EXCLUDED_SEGMENTS: frozenset[str] = frozenset({
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "third_party",
    "bin",
    "obj",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
})


def _is_excluded_segment(name: str) -> bool:
    return name in _EXCLUDED_SEGMENTS


def read_text_safely(path: Path, max_bytes: int = 10_485_760) -> str:
    """Read a file as UTF-8 with errors='ignore'. Returns '' on failure."""
    try:
        if path.stat().st_size > max_bytes:
            return ""
    except OSError:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def count_file_loc(path: Path, max_bytes: int = 10_485_760) -> int:
    """Count lines in ``path`` safely, returning 0 on error."""
    try:
        if path.stat().st_size > max_bytes:
            return 0
    except OSError:
        return 0
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0
