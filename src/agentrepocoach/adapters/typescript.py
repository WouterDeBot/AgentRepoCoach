"""TypeScript language adapter.

Detects TypeScript repos via ``tsconfig.json`` / ``package.json`` presence.
Walks ``src/`` for production files and ``tests/`` / ``test/`` / ``__tests__/``
for test files. Scans ``throw new`` statements, classifies error types, and
detects JSDoc presence above top-level declarations.

All analysis is regex-based against file text — no AST parsing, no runtime
dependencies beyond the Python 3.11+ standard library.
"""
from __future__ import annotations

import json
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

_TS_SUFFIX: tuple[str, ...] = (".ts", ".tsx")
_TS_EXCLUDE_SUFFIXES: tuple[str, ...] = (".d.ts",)
_TS_TEST_SUFFIXES: tuple[str, ...] = (".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")

# Throw-site scanning.
_THROW_PATTERN = re.compile(r"\bthrow\s+new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")

# Declaration scanning — exported (public).
_EXPORT_CLASS_PATTERN = re.compile(
    r"^export\s+(?:default\s+|abstract\s+)*(?:class|interface)\s+([A-Za-z_]\w*)"
)
_EXPORT_FUNCTION_PATTERN = re.compile(
    r"^export\s+(?:default\s+|async\s+)*function\s+([A-Za-z_]\w*)"
)
_EXPORT_ENUM_PATTERN = re.compile(
    r"^export\s+(?:const\s+)?enum\s+([A-Za-z_]\w*)"
)
_EXPORT_TYPE_PATTERN = re.compile(
    r"^export\s+type\s+([A-Za-z_]\w*)\s*[=<{]"
)
_EXPORT_CONST_PATTERN = re.compile(
    r"^export\s+const\s+([A-Za-z_]\w*)\s*[=:]"
)

# Non-exported (internal) declarations.
_INTERNAL_CLASS_PATTERN = re.compile(
    r"^(?:abstract\s+)?class\s+([A-Za-z_]\w*)"
)
_INTERNAL_FUNCTION_PATTERN = re.compile(
    r"^(?:async\s+)?function\s+([A-Za-z_]\w*)"
)
_INTERNAL_CONST_PATTERN = re.compile(
    r"^const\s+([A-Za-z_]\w*)\s*[=:]"
)

# Test method patterns (Jest/Vitest/Mocha).
_TEST_IT_PATTERN = re.compile(r"""\bit\s*\(\s*(['"`])(.+?)\1""")
_TEST_TEST_PATTERN = re.compile(r"""\btest\s*\(\s*(['"`])(.+?)\1""")

# Test naming: descriptive string — we accept anything with at least 3 words.
_TEST_DESCRIPTIVE_PATTERN = re.compile(r"^.+\s.+\s.+")

# Language-stdlib error types considered "too generic" for good agent UX.
_GENERIC_EXCEPTION_NAMES: frozenset[str] = frozenset({
    "Error",
    "TypeError",
    "RangeError",
    "ReferenceError",
    "SyntaxError",
})

_FIX_HINT_KEYWORDS: tuple[str, ...] = (
    "hint:", "fix:", "see ", "try ", "use ", "check ", "did you mean",
    "suggested fix", "to fix", "to resolve", "example:", "ensure",
    "install", "provide", "verify", "configure",
)

_PROD_DIR_CANDIDATES: tuple[str, ...] = ("src", "lib")
_TEST_DIR_CANDIDATES: tuple[str, ...] = ("tests", "test", "__tests__")


class TypeScriptAdapter(LanguageAdapter):
    """TypeScript / JavaScript adapter."""

    name = "typescript"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "tsconfig.json").is_file():
            return 1.0
        pkg_json = repo_path / "package.json"
        if pkg_json.is_file():
            try:
                data = json.loads(read_text_safely(pkg_json))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "typescript" in deps:
                    return 0.8
            except (json.JSONDecodeError, TypeError):
                pass
            return 0.3
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        production_roots = self._production_roots(repo_path)
        results: list[Path] = []
        for root in production_roots:
            for f in iter_source_files(
                root,
                suffixes=_TS_SUFFIX,
                exclude_suffixes=_TS_EXCLUDE_SUFFIXES,
            ):
                if not _is_test_file(f):
                    results.append(f)
        return results

    def find_test_files(self, repo_path: Path) -> list[Path]:
        results: list[Path] = []
        # Conventional test directories.
        for name in _TEST_DIR_CANDIDATES:
            candidate = repo_path / name
            if candidate.is_dir():
                results.extend(
                    iter_source_files(candidate, suffixes=_TS_SUFFIX, exclude_suffixes=_TS_EXCLUDE_SUFFIXES)
                )
        # Also pick up co-located test files in production directories.
        for root in self._production_roots(repo_path):
            for f in iter_source_files(root, suffixes=_TS_SUFFIX, exclude_suffixes=_TS_EXCLUDE_SUFFIXES):
                if _is_test_file(f) and f not in results:
                    results.append(f)
        return results

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Top-level directories under src/ that contain .ts files."""
        modules: set[str] = set()
        for root in self._production_roots(repo_path):
            for entry in root.iterdir():
                if entry.is_dir() and any(entry.rglob("*.ts")):
                    modules.add(entry.name)
            # If src/ has direct .ts files but no subdirectories, use the root name.
            if not modules:
                ts_files = list(root.glob("*.ts"))
                if ts_files:
                    modules.add(root.name)
        return sorted(modules)

    def _production_roots(self, repo_path: Path) -> list[Path]:
        roots: list[Path] = []
        for name in _PROD_DIR_CANDIDATES:
            candidate = repo_path / name
            if candidate.is_dir():
                roots.append(candidate)
        return roots

    # ------------------------------------------------------------------
    # Throw-site analysis
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
            for match in _THROW_PATTERN.finditer(text):
                exception_type = match.group(1)
                line_no = text.count("\n", 0, match.start()) + 1
                # Extract text from throw to closing paren/semicolon for
                # fix-hint detection (message often spans multiple lines).
                context_text = _extract_throw_context(text, match.start())
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type=exception_type,
                        has_fix_hint=_has_fix_hint(context_text, hint_marker),
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
            stripped = line.strip()

            # Try exported (public) patterns first.
            name = _match_exported(stripped)
            if name is not None:
                results.append(
                    Declaration(
                        file=path,
                        line=i + 1,
                        name=name,
                        visibility="public",
                        has_doc_comment=_has_preceding_jsdoc(lines, i),
                    )
                )
                continue

            # Try non-exported (internal) patterns — only at column 0.
            if line and not line[0].isspace():
                name = _match_internal(stripped)
                if name is not None:
                    results.append(
                        Declaration(
                            file=path,
                            line=i + 1,
                            name=name,
                            visibility="internal",
                            has_doc_comment=_has_preceding_jsdoc(lines, i),
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
            for match in _TEST_IT_PATTERN.finditer(text):
                results.append((path, match.group(2)))
            for match in _TEST_TEST_PATTERN.finditer(text):
                results.append((path, match.group(2)))
        return results

    def test_naming_pattern(self) -> re.Pattern[str]:
        return _TEST_DESCRIPTIVE_PATTERN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_throw_context(text: str, start: int, max_chars: int = 500) -> str:
    """Extract text from a throw statement through the closing paren.

    Walks forward from ``start`` up to ``max_chars`` or the matching close
    paren, whichever comes first. This captures multi-line throw messages.
    """
    end = min(start + max_chars, len(text))
    depth = 0
    for i in range(start, end):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:end]


def _is_test_file(path: Path) -> bool:
    name = path.name
    return any(name.endswith(sfx) for sfx in _TS_TEST_SUFFIXES)


def _has_fix_hint(text: str, hint_marker: str) -> bool:
    lower = text.lower()
    if hint_marker and hint_marker.lower() in lower:
        return True
    for keyword in _FIX_HINT_KEYWORDS:
        if keyword in lower:
            return True
    return False


def _match_exported(line: str) -> str | None:
    """Return the declaration name if line is an export declaration, else None."""
    for pattern in (
        _EXPORT_CLASS_PATTERN,
        _EXPORT_FUNCTION_PATTERN,
        _EXPORT_ENUM_PATTERN,
        _EXPORT_TYPE_PATTERN,
        _EXPORT_CONST_PATTERN,
    ):
        m = pattern.match(line)
        if m:
            return m.group(1)
    return None


def _match_internal(line: str) -> str | None:
    """Return the declaration name if line is a non-exported top-level declaration."""
    for pattern in (
        _INTERNAL_CLASS_PATTERN,
        _INTERNAL_FUNCTION_PATTERN,
        _INTERNAL_CONST_PATTERN,
    ):
        m = pattern.match(line)
        if m:
            return m.group(1)
    return None


def _has_preceding_jsdoc(lines: list[str], index: int) -> bool:
    """Walk backwards from ``index``. Return True if the first non-blank line
    above ends with ``*/`` (closing a JSDoc block).
    """
    j = index - 1
    while j >= 0:
        stripped = lines[j].strip()
        if stripped == "":
            j -= 1
            continue
        return stripped.endswith("*/")
    return False


TypeScriptAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
