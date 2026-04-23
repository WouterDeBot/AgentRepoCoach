"""Go language adapter.

Detects Go repos via ``go.mod`` presence. Walks the repo for production
``.go`` files (excluding ``_test.go``), scans ``return fmt.Errorf(`` /
``errors.New(`` / custom error returns, and detects Go doc comments above
exported declarations.

Go's error model differs from throw-based languages: errors are returned
values, not thrown exceptions. This adapter maps Go error-creation sites
(``fmt.Errorf``, ``errors.New``, ``&CustomError{}``) to the ``ThrowSite``
model. The "exception type" is the error constructor or custom type name.

All analysis is regex-based — no AST parsing, stdlib only.
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

_GO_SUFFIX: tuple[str, ...] = (".go",)
_GO_TEST_SUFFIX: tuple[str, ...] = ("_test.go",)

# Error-creation patterns (Go returns errors, doesn't throw them).
_ERRORS_NEW_PATTERN = re.compile(r"\berrors\.New\s*\(")
_FMT_ERRORF_PATTERN = re.compile(r"\bfmt\.Errorf\s*\(")
_CUSTOM_ERROR_PATTERN = re.compile(r"&([A-Z][A-Za-z0-9_]*Error)\s*\{")

# Declaration patterns — Go uses capitalization for visibility.
_FUNC_PATTERN = re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)\s*\(")
_TYPE_PATTERN = re.compile(r"^type\s+([A-Za-z_]\w*)\s+(?:struct|interface|int|string)")
_CONST_VAR_PATTERN = re.compile(r"^(?:var|const)\s+([A-Za-z_]\w*)\s")

# Test function pattern.
_TEST_FUNC_PATTERN = re.compile(r"^func\s+(Test[A-Z]\w*)\s*\(")
# Go convention: TestFoo_Bar_Baz or TestFooBar.
_TEST_NAMING_PATTERN = re.compile(r"^Test[A-Z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+$")

# Generic error constructors (too generic for good agent UX).
_GENERIC_ERROR_NAMES: frozenset[str] = frozenset({
    "errors.New",
    "fmt.Errorf",
})

_FIX_HINT_KEYWORDS: tuple[str, ...] = (
    "hint:", "fix:", "see ", "try ", "use ", "check ", "did you mean",
    "suggested fix", "to fix", "to resolve", "example:", "ensure",
    "install", "provide", "verify", "configure", "expected",
)

_TEST_DIR_CANDIDATES: tuple[str, ...] = ("test", "tests", "internal/test")


class GoAdapter(LanguageAdapter):
    """Go adapter."""

    name = "go"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "go.mod").is_file():
            return 1.0
        if any(repo_path.rglob("*.go")):
            return 0.5
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        all_go = iter_source_files(repo_path, suffixes=_GO_SUFFIX)
        return [f for f in all_go if not _is_test_file(f)]

    def find_test_files(self, repo_path: Path) -> list[Path]:
        all_go = iter_source_files(repo_path, suffixes=_GO_SUFFIX)
        return [f for f in all_go if _is_test_file(f)]

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Return Go package directory names containing production .go files."""
        modules: set[str] = set()
        for f in self.find_production_files(repo_path):
            # Use the parent directory name as the module/package name.
            pkg = f.parent.name
            if pkg and pkg != repo_path.name:
                modules.add(pkg)
        # If all files are at repo root, use the module name from go.mod.
        if not modules:
            mod_file = repo_path / "go.mod"
            if mod_file.is_file():
                text = read_text_safely(mod_file)
                m = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
                if m:
                    modules.add(m.group(1).rsplit("/", 1)[-1])
        return sorted(modules)

    # ------------------------------------------------------------------
    # Throw-site analysis (Go: error-creation sites)
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

            # errors.New() sites
            for match in _ERRORS_NEW_PATTERN.finditer(text):
                context = _extract_context(text, match.start())
                line_no = text.count("\n", 0, match.start()) + 1
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type="errors.New",
                        has_fix_hint=_has_fix_hint(context, hint_marker),
                        is_user_defined=False,
                        is_generic=True,
                    )
                )

            # fmt.Errorf() sites
            for match in _FMT_ERRORF_PATTERN.finditer(text):
                context = _extract_context(text, match.start())
                line_no = text.count("\n", 0, match.start()) + 1
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type="fmt.Errorf",
                        has_fix_hint=_has_fix_hint(context, hint_marker),
                        is_user_defined=False,
                        is_generic=True,
                    )
                )

            # Custom error types: &CustomError{}
            for match in _CUSTOM_ERROR_PATTERN.finditer(text):
                error_type = match.group(1)
                context = _extract_context(text, match.start())
                line_no = text.count("\n", 0, match.start()) + 1
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type=error_type,
                        has_fix_hint=_has_fix_hint(context, hint_marker),
                        is_user_defined=error_type in domain_exception_types,
                        is_generic=False,
                    )
                )
        return sites

    def generic_exception_names(self) -> set[str]:
        return set(_GENERIC_ERROR_NAMES)

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
            name = _match_declaration(line)
            if name is None:
                continue
            # Go visibility: uppercase first letter = exported (public).
            visibility = "public" if name[0].isupper() else "internal"
            results.append(
                Declaration(
                    file=path,
                    line=i + 1,
                    name=name,
                    visibility=visibility,
                    has_doc_comment=_has_preceding_go_doc(lines, i),
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
            for line in text.splitlines():
                m = _TEST_FUNC_PATTERN.match(line)
                if m:
                    results.append((path, m.group(1)))
        return results

    def test_naming_pattern(self) -> re.Pattern[str]:
        return _TEST_NAMING_PATTERN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    return path.name.endswith("_test.go")


def _extract_context(text: str, start: int, max_chars: int = 500) -> str:
    """Extract text from start through the next closing paren or brace."""
    end = min(start + max_chars, len(text))
    depth = 0
    for i in range(start, end):
        ch = text[i]
        if ch in ("(", "{"):
            depth += 1
        elif ch in (")", "}"):
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:end]


def _has_fix_hint(text: str, hint_marker: str) -> bool:
    lower = text.lower()
    if hint_marker and hint_marker.lower() in lower:
        return True
    for keyword in _FIX_HINT_KEYWORDS:
        if keyword in lower:
            return True
    return False


def _match_declaration(line: str) -> str | None:
    """Return the declaration name if the line declares a func, type, or var/const."""
    for pattern in (_FUNC_PATTERN, _TYPE_PATTERN, _CONST_VAR_PATTERN):
        m = pattern.match(line)
        if m:
            return m.group(1)
    return None


def _has_preceding_go_doc(lines: list[str], index: int) -> bool:
    """Return True if the line above is a Go doc comment (``//`` comment block)."""
    j = index - 1
    while j >= 0:
        stripped = lines[j].strip()
        if stripped == "":
            j -= 1
            continue
        return stripped.startswith("//")
    return False


GoAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
