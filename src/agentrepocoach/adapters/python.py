"""Python language adapter.

Detects Python repos via ``pyproject.toml`` / ``setup.py`` presence. Walks
``src/`` or top-level packages for production files and ``tests/`` / ``test/``
for test files. Scans ``raise`` statements, classifies exception types, and
detects docstring presence above top-level declarations.

Deliberately minimal: this adapter is new at launch and not research-backed
to the same degree as the C# adapter. A "Python adapter validation" doc
published post-launch will compare scores on 3 popular Python repos.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .base import (
    Declaration,
    LanguageAdapter,
    ThrowSite,
    count_file_loc,
    iter_source_files,
    read_text_safely,
)

_PYTHON_SUFFIX: tuple[str, ...] = (".py",)

_RAISE_PATTERN = re.compile(r"\braise\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|$)")

_PUBLIC_DECL_PATTERN = re.compile(r"^(class|def)\s+([A-Za-z][A-Za-z0-9_]*)\s*[\(:]")
_PRIVATE_DECL_PATTERN = re.compile(r"^(class|def)\s+(_[A-Za-z0-9_]*)\s*[\(:]")

_TEST_METHOD_PATTERN = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(", re.MULTILINE)
_TEST_SNAKE_PATTERN = re.compile(r"^test_[a-z][a-z0-9_]*_[a-z0-9_]+_[a-z0-9_]+$")

# Stdlib exception types considered "too generic" for good agent UX.
_GENERIC_EXCEPTION_NAMES: frozenset[str] = frozenset({
    "Exception",
    "BaseException",
    "RuntimeError",
    "ValueError",
    "TypeError",
})

_PROD_DIR_CANDIDATES: tuple[str, ...] = ("src", "lib")
_TEST_DIR_CANDIDATES: tuple[str, ...] = ("tests", "test")


class PythonAdapter(LanguageAdapter):
    """Python adapter. MVP implementation."""

    name = "python"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "pyproject.toml").is_file():
            return 1.0
        if (repo_path / "setup.py").is_file():
            return 0.9
        if any(repo_path.rglob("*.py")):
            return 0.6
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        production_roots = self._production_roots(repo_path)
        results: list[Path] = []
        for root in production_roots:
            results.extend(iter_source_files(root, suffixes=_PYTHON_SUFFIX))
        return results

    def find_test_files(self, repo_path: Path) -> list[Path]:
        results: list[Path] = []
        for name in _TEST_DIR_CANDIDATES:
            candidate = repo_path / name
            if candidate.is_dir():
                results.extend(iter_source_files(candidate, suffixes=_PYTHON_SUFFIX))
        return results

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Top-level package directories under src/ or the repo root."""
        modules: set[str] = set()
        for root in self._production_roots(repo_path):
            for entry in root.iterdir():
                if entry.is_dir() and (entry / "__init__.py").is_file():
                    modules.add(entry.name)
        return sorted(modules)

    def _production_roots(self, repo_path: Path) -> list[Path]:
        roots: list[Path] = []
        for name in _PROD_DIR_CANDIDATES:
            candidate = repo_path / name
            if candidate.is_dir():
                roots.append(candidate)
        if not roots:
            # Fall back: top-level packages in the repo root that are NOT tests.
            for entry in repo_path.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name in _TEST_DIR_CANDIDATES:
                    continue
                if entry.name.startswith("."):
                    continue
                if (entry / "__init__.py").is_file():
                    roots.append(entry)
        return roots

    # ------------------------------------------------------------------
    # Throw-site analysis (Python: raise sites)
    # ------------------------------------------------------------------

    def scan_throw_sites(
        self,
        files: Iterable[Path],
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        sites: list[ThrowSite] = []
        for path in files:
            text = read_text_safely(path)
            if not text:
                continue
            for match in _RAISE_PATTERN.finditer(text):
                exception_type = match.group(1)
                line_no = text.count("\n", 0, match.start()) + 1
                # Lightweight message extraction: take the rest of the line.
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.start())
                if line_end == -1:
                    line_end = len(text)
                line_text = text[line_start:line_end]
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type=exception_type,
                        has_fix_hint=_has_fix_hint(line_text, hint_marker),
                        is_user_defined=exception_type in domain_exception_types,
                        is_generic=exception_type in _GENERIC_EXCEPTION_NAMES,
                    )
                )
        return sites

    def generic_exception_names(self) -> set[str]:
        return set(_GENERIC_EXCEPTION_NAMES)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def scan_declarations(self, files: Iterable[Path]) -> list[Declaration]:
        declarations: list[Declaration] = []
        for path in files:
            text = read_text_safely(path)
            if not text:
                continue
            declarations.extend(self._scan_declarations_in_text(path, text))
        return declarations

    def _scan_declarations_in_text(self, path: Path, text: str) -> list[Declaration]:
        lines = text.splitlines()
        results: list[Declaration] = []
        for i, line in enumerate(lines):
            if line.startswith(" ") or line.startswith("\t"):
                # Only top-level declarations.
                continue
            public_match = _PUBLIC_DECL_PATTERN.match(line)
            if public_match and not public_match.group(2).startswith("_"):
                results.append(
                    Declaration(
                        file=path,
                        line=i + 1,
                        name=public_match.group(2),
                        visibility="public",
                        has_doc_comment=_has_following_docstring(lines, i),
                    )
                )
                continue
            private_match = _PRIVATE_DECL_PATTERN.match(line)
            if private_match:
                results.append(
                    Declaration(
                        file=path,
                        line=i + 1,
                        name=private_match.group(2),
                        visibility="private",
                        has_doc_comment=_has_following_docstring(lines, i),
                    )
                )
        return results

    # ------------------------------------------------------------------
    # Test methods
    # ------------------------------------------------------------------

    def find_test_methods(self, files: Iterable[Path]) -> list[tuple[Path, str]]:
        results: list[tuple[Path, str]] = []
        for path in files:
            text = read_text_safely(path)
            if not text:
                continue
            for match in _TEST_METHOD_PATTERN.finditer(text):
                results.append((path, match.group(1)))
        return results

    def test_naming_pattern(self) -> re.Pattern[str]:
        return _TEST_SNAKE_PATTERN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_fix_hint(text: str, hint_marker: str) -> bool:
    lower = text.lower()
    if hint_marker and hint_marker.lower() in lower:
        return True
    for phrase in ("hint:", "fix:", "see ", "try ", "use ", "check ", "did you mean"):
        if phrase in lower:
            return True
    return False


def _has_following_docstring(lines: list[str], index: int) -> bool:
    """Return True if the next non-blank line after ``index`` starts a docstring."""
    j = index + 1
    while j < len(lines):
        stripped = lines[j].strip()
        if stripped == "":
            j += 1
            continue
        return stripped.startswith('"""') or stripped.startswith("'''")
    return False


PythonAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
