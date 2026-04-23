"""Rust language adapter.

Detects Rust repos via ``Cargo.toml`` presence. Walks ``src/`` for production
``.rs`` files and scans for error-creation patterns. Rust uses ``Result<T, E>``
rather than exceptions — this adapter maps error-creation sites (``panic!``,
custom error types, ``anyhow!``, ``bail!``) to the ``ThrowSite`` model.

Declarations are detected via ``pub fn``, ``pub struct``, ``pub enum``, etc.
Doc comments use ``///`` (outer) or ``//!`` (inner) prefixes.

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

_RUST_SUFFIX: tuple[str, ...] = (".rs",)

# Error-creation patterns.
_PANIC_PATTERN = re.compile(r"\bpanic!\s*\(")
_ANYHOW_PATTERN = re.compile(r"\b(?:anyhow!|bail!)\s*\(")
_CUSTOM_ERROR_RETURN = re.compile(r"\bErr\s*\(\s*([A-Z][A-Za-z0-9_]*(?:::[A-Z]\w*)?)\s*[({]")

# Declaration patterns.
_PUB_DECL_PATTERN = re.compile(
    r"^pub(?:\s*\(crate\))?\s+(?:async\s+)?(?:fn|struct|enum|trait|type|const|static|mod)\s+([A-Za-z_]\w*)"
)
_PRIVATE_DECL_PATTERN = re.compile(
    r"^(?:async\s+)?(?:fn|struct|enum|trait|type|const|static)\s+([A-Za-z_]\w*)"
)

# Test function pattern.
_TEST_FN_PATTERN = re.compile(r"^\s*(?:async\s+)?fn\s+(test_\w+)\s*\(")
_TEST_ATTR_PATTERN = re.compile(r"^\s*#\[test\]")
# Rust test naming: test_something_does_something.
_TEST_NAMING_PATTERN = re.compile(r"^test_[a-z][a-z0-9_]*_[a-z0-9_]+$")

# Generic panic types.
_GENERIC_ERROR_NAMES: frozenset[str] = frozenset({
    "panic!",
    "anyhow!",
    "bail!",
})

_FIX_HINT_KEYWORDS: tuple[str, ...] = (
    "hint:", "fix:", "see ", "try ", "use ", "check ", "did you mean",
    "suggested fix", "to fix", "to resolve", "example:", "ensure",
    "expected", "must be", "should be",
)


class RustAdapter(LanguageAdapter):
    """Rust adapter."""

    name = "rust"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "Cargo.toml").is_file():
            return 1.0
        # Shallow search (root + one level) to avoid false positives from
        # test fixtures or vendored dependencies.
        if any(repo_path.glob("*.rs")) or any(repo_path.glob("*/*.rs")):
            return 0.5
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        src_dir = repo_path / "src"
        if src_dir.is_dir():
            return iter_source_files(src_dir, suffixes=_RUST_SUFFIX)
        return iter_source_files(repo_path, suffixes=_RUST_SUFFIX)

    def find_test_files(self, repo_path: Path) -> list[Path]:
        results: list[Path] = []
        tests_dir = repo_path / "tests"
        if tests_dir.is_dir():
            results.extend(iter_source_files(tests_dir, suffixes=_RUST_SUFFIX))
        # In Rust, test modules are often inline (#[cfg(test)]) in prod files.
        # We also look for dedicated test files in src/.
        return results

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Return crate name from Cargo.toml and top-level module names."""
        modules: set[str] = set()
        cargo = repo_path / "Cargo.toml"
        if cargo.is_file():
            text = read_text_safely(cargo)
            m = re.search(r'name\s*=\s*"([^"]+)"', text)
            if m:
                modules.add(m.group(1))
        src_dir = repo_path / "src"
        if src_dir.is_dir():
            for entry in src_dir.iterdir():
                if entry.is_dir() and any(entry.rglob("*.rs")):
                    modules.add(entry.name)
                elif entry.is_file() and entry.suffix == ".rs" and entry.name not in ("main.rs", "lib.rs"):
                    modules.add(entry.stem)
        return sorted(modules)

    # ------------------------------------------------------------------
    # Throw-site analysis (Rust: panic!, bail!, Err(CustomError))
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

            # panic!() sites
            for match in _PANIC_PATTERN.finditer(text):
                context = _extract_context(text, match.start())
                line_no = text.count("\n", 0, match.start()) + 1
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type="panic!",
                        has_fix_hint=_has_fix_hint(context, hint_marker),
                        is_user_defined=False,
                        is_generic=True,
                    )
                )

            # anyhow!/bail! sites
            for match in _ANYHOW_PATTERN.finditer(text):
                context = _extract_context(text, match.start())
                line_no = text.count("\n", 0, match.start()) + 1
                err_type = "anyhow!" if "anyhow!" in match.group() else "bail!"
                sites.append(
                    ThrowSite(
                        file=path,
                        line=line_no,
                        exception_type=err_type,
                        has_fix_hint=_has_fix_hint(context, hint_marker),
                        is_user_defined=False,
                        is_generic=True,
                    )
                )

            # Err(CustomError{}) or Err(CustomError(...))
            for match in _CUSTOM_ERROR_RETURN.finditer(text):
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
            # Try pub declarations first.
            m = _PUB_DECL_PATTERN.match(line)
            if m:
                visibility = "internal" if "pub(crate)" in line else "public"
                results.append(
                    Declaration(
                        file=path,
                        line=i + 1,
                        name=m.group(1),
                        visibility=visibility,
                        has_doc_comment=_has_preceding_doc_comment(lines, i),
                    )
                )
                continue
            # Try private (no pub) declarations — only at column 0.
            if not line.startswith(" ") and not line.startswith("\t"):
                m = _PRIVATE_DECL_PATTERN.match(line)
                if m:
                    results.append(
                        Declaration(
                            file=path,
                            line=i + 1,
                            name=m.group(1),
                            visibility="private",
                            has_doc_comment=_has_preceding_doc_comment(lines, i),
                        )
                    )
        return results

    # ------------------------------------------------------------------
    # Test methods
    # ------------------------------------------------------------------

    def find_test_methods(self, files: Iterable[Path]) -> list[tuple[Path, str]]:
        """Find test functions in both dedicated test files and inline #[test] modules."""
        results: list[tuple[Path, str]] = []
        all_files = list(files)
        # Also scan production files for inline tests.
        for path in all_files:
            text = read_text_safely(path)
            if not text:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines):
                m = _TEST_FN_PATTERN.match(line)
                if m:
                    results.append((path, m.group(1)))
                    continue
                # Also detect functions preceded by #[test] attribute.
                if _TEST_ATTR_PATTERN.match(line):
                    # Next non-blank, non-attribute line should be the fn.
                    for j in range(i + 1, min(i + 5, len(lines))):
                        fn_match = re.match(r"^\s*(?:async\s+)?fn\s+(\w+)\s*\(", lines[j])
                        if fn_match:
                            results.append((path, fn_match.group(1)))
                            break
        return results

    def test_naming_pattern(self) -> re.Pattern[str]:
        return _TEST_NAMING_PATTERN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_context(text: str, start: int, max_chars: int = 500) -> str:
    """Extract text from start through the next closing paren/brace."""
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


def _has_preceding_doc_comment(lines: list[str], index: int) -> bool:
    """Return True if the line above is a Rust doc comment (``///`` or ``//!``)."""
    j = index - 1
    while j >= 0:
        stripped = lines[j].strip()
        if stripped == "":
            j -= 1
            continue
        return stripped.startswith("///") or stripped.startswith("//!")
    return False


RustAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
