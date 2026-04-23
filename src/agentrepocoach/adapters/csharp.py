"""C# language adapter.

Auto-discovers production modules by scanning ``*.csproj`` files at the repo
root and mapping each project's containing directory to a production source
tree. Tests directories are detected by conventional naming (``*.Tests``,
``*Test``) and by ``*Tests.csproj`` filename patterns.

Throw-site scanning is ported from the methodology research throw-site
extractor — a minimal C# tokenizer that walks ``throw new <Name>Exception(``
sites, extracts the message argument text, and classifies each site by:

- ``exception_type`` — the C# type name raised
- ``has_fix_hint`` — does the message contain the configured hint marker
- ``is_user_defined`` — is the type declared inside the repo (user exception)
- ``is_generic`` — is the type one of the language-stdlib "too generic" names
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

# Source-file patterns.
_CSHARP_SUFFIX: tuple[str, ...] = (".cs",)
_CSHARP_EXCLUDE_SUFFIXES: tuple[str, ...] = (".Designer.cs", ".g.cs", ".g.i.cs")
_CSHARP_EXCLUDE_PATH_SUBSTRINGS: tuple[str, ...] = ("/bin/", "/obj/")

# Throw-site scanning.
_THROW_PATTERN = re.compile(r"\bthrow\s+new\s+([A-Za-z_][A-Za-z0-9_]*Exception)\s*\(")

# Declaration scanning.
_PUBLIC_DECL_PATTERN = re.compile(
    r"\bpublic\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)*"
    r"(?:class|interface|record|enum|struct)\s+(\w+)",
)
_INTERNAL_DECL_PATTERN = re.compile(
    r"\binternal\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)*"
    r"(?:class|interface|record|enum|struct)\s+(\w+)",
)
_PRIVATE_DECL_PATTERN = re.compile(
    r"\bprivate\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)*"
    r"(?:class|interface|record|enum|struct)\s+(\w+)",
)

# Test-method naming conventions (xUnit / NUnit / MSTest Method_Scenario_Expected).
_TEST_METHOD_PATTERN = re.compile(r"\bpublic\s+(?:async\s+)?(?:Task|void)\s+(\w+)\s*\(")
_MSE_NAMING_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9]+_[A-Za-z0-9]+")

# Keywords that indicate an actionable fix hint in an error message. These are
# intentionally simple substrings (case-insensitive) so adapters do not need a
# full natural-language parser.
_FIX_HINT_WORD_KEYWORDS: tuple[str, ...] = (
    "run",
    "use",
    "try",
    "check",
    "see",
    "set",
    "add",
    "install",
    "provide",
    "ensure",
    "verify",
    "enable",
    "configure",
    "register",
    "retry",
    "rerun",
)
_FIX_HINT_SUBSTRING_KEYWORDS: tuple[str, ...] = (
    "did you mean",
    "available:",
    "expected:",
    "allowed:",
    "supported:",
    "valid:",
    "valid values:",
    "matches:",
    "hint:",
    "fix:",
    "example:",
    "to fix",
    "to resolve",
    "suggested fix",
    "environment variable",
    ".md",
    ".json",
    ".cs",
)

# Language-stdlib exception types considered "too generic" for good agent UX.
_GENERIC_EXCEPTION_NAMES: frozenset[str] = frozenset({
    "Exception",
    "SystemException",
    "InvalidOperationException",
    "ApplicationException",
})


class CSharpAdapter(LanguageAdapter):
    """C# / .NET adapter. MVP implementation."""

    name = "csharp"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        """1.0 if any *.sln, 0.8 if any *.csproj, else 0.0.

        Only checks the repo root and one level deep to avoid false
        positives from test fixtures or vendored dependencies.
        """
        if any(repo_path.glob("*.sln")) or any(repo_path.glob("*/*.sln")):
            return 1.0
        if any(repo_path.glob("*.csproj")) or any(repo_path.glob("*/*.csproj")):
            return 0.8
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        """Return all production *.cs files, skipping bin/obj/generated files."""
        project_dirs = self._find_production_project_dirs(repo_path)
        results: list[Path] = []
        for proj_dir in project_dirs:
            results.extend(self._iter_cs_files(proj_dir))
        return results

    def find_test_files(self, repo_path: Path) -> list[Path]:
        """Return all test *.cs files (projects whose name matches test conventions)."""
        project_dirs = self._find_test_project_dirs(repo_path)
        results: list[Path] = []
        for proj_dir in project_dirs:
            results.extend(self._iter_cs_files(proj_dir))
        return results

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Return logical project names for every production *.csproj."""
        names: list[str] = []
        for proj_path in self._iter_csproj_files(repo_path):
            if self._looks_like_test_project(proj_path):
                continue
            names.append(proj_path.stem)
        return sorted(set(names))

    def _iter_csproj_files(self, repo_path: Path) -> list[Path]:
        return [
            p for p in repo_path.rglob("*.csproj")
            if "/bin/" not in str(p) and "/obj/" not in str(p)
        ]

    def _find_production_project_dirs(self, repo_path: Path) -> list[Path]:
        return [
            proj.parent for proj in self._iter_csproj_files(repo_path)
            if not self._looks_like_test_project(proj)
        ]

    def _find_test_project_dirs(self, repo_path: Path) -> list[Path]:
        return [
            proj.parent for proj in self._iter_csproj_files(repo_path)
            if self._looks_like_test_project(proj)
        ]

    @staticmethod
    def _looks_like_test_project(csproj_path: Path) -> bool:
        name = csproj_path.stem.lower()
        return name.endswith(".tests") or name.endswith("tests") or name.endswith(".test")

    def _iter_cs_files(self, dir_path: Path) -> list[Path]:
        return iter_source_files(
            dir_path,
            suffixes=_CSHARP_SUFFIX,
            exclude_substrings=_CSHARP_EXCLUDE_PATH_SUBSTRINGS,
            exclude_suffixes=_CSHARP_EXCLUDE_SUFFIXES,
        )

    # ------------------------------------------------------------------
    # Throw-site analysis
    # ------------------------------------------------------------------

    def scan_throw_sites(
        self,
        files: Iterable[Path],
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        """Scan every file for ``throw new X(...)`` sites."""
        sites: list[ThrowSite] = []
        for path in files:
            text = read_text_safely(path)
            if not text:
                continue
            sites.extend(
                self._scan_throw_sites_in_text(
                    path,
                    text,
                    hint_marker,
                    domain_exception_types,
                )
            )
        return sites

    def _scan_throw_sites_in_text(
        self,
        path: Path,
        text: str,
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        results: list[ThrowSite] = []
        for match in _THROW_PATTERN.finditer(text):
            exception_type = match.group(1)
            paren_start = match.end() - 1
            args_text, _ = _extract_throw_message(text, paren_start)
            line_no = text.count("\n", 0, match.start()) + 1
            results.append(
                ThrowSite(
                    file=path,
                    line=line_no,
                    exception_type=exception_type,
                    has_fix_hint=_has_fix_hint(args_text, hint_marker),
                    is_user_defined=exception_type in domain_exception_types,
                    is_generic=exception_type in _GENERIC_EXCEPTION_NAMES,
                )
            )
        return results

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
            visibility = _declaration_visibility(line)
            if visibility is None:
                continue
            name_match = _declaration_name(line, visibility)
            if name_match is None:
                continue
            has_doc = _has_preceding_xml_doc(lines, i)
            results.append(
                Declaration(
                    file=path,
                    line=i + 1,
                    name=name_match,
                    visibility=visibility,
                    has_doc_comment=has_doc,
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
        return _MSE_NAMING_PATTERN


# ---------------------------------------------------------------------------
# Module-level helpers (kept outside the class so they can be unit-tested
# without instantiating the adapter).
# ---------------------------------------------------------------------------


def _extract_throw_message(source: str, start: int) -> tuple[str, int]:
    """Walk from the opening paren at ``start`` to the matching close-paren.

    Handles nested parens, string literals (including verbatim @"..." and
    escaped), and line comments. Returns the argument text and the index
    just past the closing paren. This is a minimal C# tokenizer good enough
    for throw-site message extraction.
    """
    depth = 1
    i = start + 1
    n = len(source)
    buf: list[str] = []

    while i < n and depth > 0:
        ch = source[i]

        # String literals.
        if ch == '"':
            buf.append(ch)
            i += 1
            is_verbatim = i >= 2 and source[i - 2] == "@"
            while i < n:
                cur = source[i]
                buf.append(cur)
                if is_verbatim:
                    if cur == '"':
                        if i + 1 < n and source[i + 1] == '"':
                            buf.append(source[i + 1])
                            i += 2
                            continue
                        i += 1
                        break
                    i += 1
                else:
                    if cur == "\\" and i + 1 < n:
                        buf.append(source[i + 1])
                        i += 2
                        continue
                    if cur == '"':
                        i += 1
                        break
                    i += 1
            continue

        # Line comments.
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return "".join(buf), i + 1
        buf.append(ch)
        i += 1

    return "".join(buf), i


def _has_fix_hint(message_text: str, hint_marker: str) -> bool:
    """Return True if the message text contains any fix-hint signal.

    The configurable ``hint_marker`` (e.g. "Suggested fix:") is matched first.
    If absent, a small set of generic action-verb and substring keywords is
    checked.
    """
    lower = message_text.lower()
    if hint_marker and hint_marker.lower() in lower:
        return True
    for substring in _FIX_HINT_SUBSTRING_KEYWORDS:
        if substring in lower:
            return True
    # Word-bounded action verbs.
    for verb in _FIX_HINT_WORD_KEYWORDS:
        if re.search(rf"\b{re.escape(verb)}\b", lower):
            return True
    return False


def _declaration_visibility(line: str) -> str | None:
    if _PUBLIC_DECL_PATTERN.search(line):
        return "public"
    if _INTERNAL_DECL_PATTERN.search(line):
        return "internal"
    if _PRIVATE_DECL_PATTERN.search(line):
        return "private"
    return None


def _declaration_name(line: str, visibility: str) -> str | None:
    patterns = {
        "public": _PUBLIC_DECL_PATTERN,
        "internal": _INTERNAL_DECL_PATTERN,
        "private": _PRIVATE_DECL_PATTERN,
    }
    match = patterns[visibility].search(line)
    return match.group(1) if match else None


def _has_preceding_xml_doc(lines: list[str], index: int) -> bool:
    """Walk backwards past attributes / blank lines. Return True if the first
    non-attribute / non-blank line above ``index`` starts with ``///``.
    """
    j = index - 1
    while j >= 0:
        stripped = lines[j].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            j -= 1
            continue
        if stripped == "":
            j -= 1
            continue
        return stripped.startswith("///")
    return False


# Expose count_file_loc for components to use via adapter.
CSharpAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
