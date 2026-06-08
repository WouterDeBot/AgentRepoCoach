"""Java language adapter.

Detects Java repos via ``pom.xml`` / ``build.gradle`` / ``build.gradle.kts``
presence. Walks the repo for production ``.java`` files (excluding
``*Test.java`` / ``Test*.java``), scans ``throw new`` statements, classifies
exception types, and detects Javadoc comment presence above public
declarations.

Java's throw model maps directly to the ``ThrowSite`` model: every
``throw new SomeException(...)`` statement is a candidate.  Javadoc blocks
(``/** ... */``) above a declaration satisfy the doc-comment requirement.

All analysis is regex-based — no AST parsing, no runtime dependencies beyond
the Python 3.11+ standard library.
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

_JAVA_SUFFIX: tuple[str, ...] = (".java",)

# Throw-site scanning — matches "throw new SomethingException(" and
# "throw new SomethingError(".
_THROW_EXCEPTION_PATTERN = re.compile(
    r"\bthrow\s+new\s+([A-Z][A-Za-z0-9_]*Exception)\s*\("
)
_THROW_ERROR_PATTERN = re.compile(
    r"\bthrow\s+new\s+([A-Z][A-Za-z0-9_]*Error)\s*\("
)

# Declaration scanning — public/protected methods, classes, interfaces, enums.
# Matches lines like:
#   public class Foo {
#   public static String doThing(
#   protected void helper(
#   public interface Runnable {
#   public enum Status {
_DECLARATION_PATTERN = re.compile(
    r"^(?:public|protected)\s+"
    r"(?:static\s+|abstract\s+|final\s+|synchronized\s+|default\s+)*"
    r"(?:[A-Za-z<>\[\]]+\s+)?"
    r"([A-Za-z_]\w*)\s*[({]"
)

# Test method detection — JUnit 4/5 @Test annotation.
_TEST_ANNOTATION_PATTERN = re.compile(r"^\s*@Test\b")

# Test method name pattern — JUnit 4 convention: testFoo / testSomethingHappens.
# JUnit 5 uses any descriptive name, but testXxx is the dominant convention.
_TEST_METHOD_PATTERN = re.compile(r"^\s+(?:public\s+|protected\s+)?void\s+(test[A-Z]\w*|should[A-Z]\w*|when[A-Z]\w*)\s*\(")

# JUnit 5 test naming: testSomething / shouldDoThing / whenConditionThenResult.
_TEST_NAMING_PATTERN = re.compile(r"^(?:test[A-Z]|should[A-Z]|when[A-Z])[A-Za-z0-9_]+$")

# Java stdlib/JDK exception types considered "too generic" for good agent UX.
_GENERIC_EXCEPTION_NAMES: frozenset[str] = frozenset({
    "Exception",
    "RuntimeException",
    "Throwable",
    "Error",
    "IllegalArgumentException",
    "IllegalStateException",
    "NullPointerException",
    "UnsupportedOperationException",
})

_FIX_HINT_KEYWORDS: tuple[str, ...] = (
    "hint:", "fix:", "see ", "try ", "use ", "check ", "did you mean",
    "suggested fix:", "to fix", "to resolve", "example:", "ensure",
    "install", "provide", "verify", "configure", "expected",
)

# Maven / Gradle build descriptor file names.
_BUILD_FILE_NAMES: tuple[str, ...] = ("pom.xml", "build.gradle", "build.gradle.kts")

# Java test file naming conventions (JUnit).
_TEST_FILE_PREFIXES: tuple[str, ...] = ("Test",)
_TEST_FILE_SUFFIXES: tuple[str, ...] = ("Test.java", "Tests.java", "TestCase.java")

# Maven standard source layout — used to discover test directories.
_TEST_DIR_CANDIDATES: tuple[str, ...] = (
    "src/test/java",
    "src/test",
    "test",
    "tests",
)


class JavaAdapter(LanguageAdapter):
    """Java adapter — Maven and Gradle projects."""

    name = "java"

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, repo_path: Path) -> float:
        # Strong signal: a build descriptor at the repo root.
        for build_file in _BUILD_FILE_NAMES:
            if (repo_path / build_file).is_file():
                return 1.0
        # Moderate signal: .java files at root or one level deep.
        if any(repo_path.glob("*.java")) or any(repo_path.glob("*/*.java")):
            return 0.8
        return 0.0

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_production_files(self, repo_path: Path) -> list[Path]:
        all_java = iter_source_files(repo_path, suffixes=_JAVA_SUFFIX)
        return [f for f in all_java if not _is_test_file(f)]

    def find_test_files(self, repo_path: Path) -> list[Path]:
        all_java = iter_source_files(repo_path, suffixes=_JAVA_SUFFIX)
        results: list[Path] = []
        seen: set[Path] = set()
        for path in all_java:
            if _is_test_file(path) and path not in seen:
                results.append(path)
                seen.add(path)
        # Also include files in recognised test directories that contain @Test
        # even if they don't follow the naming convention.
        for test_dir_rel in _TEST_DIR_CANDIDATES:
            test_dir = repo_path / test_dir_rel
            if test_dir.is_dir():
                for path in iter_source_files(test_dir, suffixes=_JAVA_SUFFIX):
                    if path not in seen:
                        text = read_text_safely(path)
                        if _TEST_ANNOTATION_PATTERN.search(text):
                            results.append(path)
                            seen.add(path)
        return results

    def find_production_modules(self, repo_path: Path) -> list[str]:
        """Return Java package names from production files.

        Uses the parent directory name of each production file as a module
        indicator.  Falls back to the Maven ``groupId`` from ``pom.xml`` when
        no subdirectories exist.
        """
        modules: set[str] = set()
        for f in self.find_production_files(repo_path):
            pkg = f.parent.name
            if pkg and pkg != repo_path.name:
                modules.add(pkg)
        if not modules:
            pom = repo_path / "pom.xml"
            if pom.is_file():
                text = read_text_safely(pom)
                m = re.search(r"<groupId>([^<]+)</groupId>", text)
                if m:
                    # Use the last component of the group ID as the module name.
                    modules.add(m.group(1).rsplit(".", 1)[-1])
        return sorted(modules)

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
            sites.extend(
                self._scan_throw_sites_in_text(path, text, hint_marker, domain_exception_types)
            )
        return sites

    def _scan_throw_sites_in_text(
        self,
        path: Path,
        text: str,
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        sites: list[ThrowSite] = []
        for pattern in (_THROW_EXCEPTION_PATTERN, _THROW_ERROR_PATTERN):
            for match in pattern.finditer(text):
                exception_type = match.group(1)
                line_no = text.count("\n", 0, match.start()) + 1
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
            # Only match declarations that start at the beginning of the line
            # (after optional indentation) — skip deeply nested inner code.
            stripped = line.lstrip()
            m = _DECLARATION_PATTERN.match(stripped)
            if m is None:
                continue
            name = m.group(1)
            # Skip Java keywords that may appear in a modifier list but are
            # not declaration names (e.g. "void", "class", "static").
            if name in {"void", "class", "interface", "enum", "abstract", "static", "final", "public", "protected", "private"}:
                continue
            visibility = "public" if stripped.startswith("public") else "internal"
            results.append(
                Declaration(
                    file=path,
                    line=i + 1,
                    name=name,
                    visibility=visibility,
                    has_doc_comment=_has_preceding_javadoc(lines, i),
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
            results.extend(self._find_test_methods_in_text(path, text))
        return results

    def _find_test_methods_in_text(
        self, path: Path, text: str
    ) -> list[tuple[Path, str]]:
        lines = text.splitlines()
        results: list[tuple[Path, str]] = []
        pending_test = False
        for line in lines:
            if _TEST_ANNOTATION_PATTERN.match(line):
                pending_test = True
                continue
            if pending_test:
                m = _TEST_METHOD_PATTERN.match(line)
                if m:
                    results.append((path, m.group(1)))
                # Also accept any method following @Test that doesn't match
                # the naming heuristic — capture the method name anyway.
                elif re.match(r"^\s+(?:public\s+|protected\s+)?void\s+(\w+)\s*\(", line):
                    mm = re.match(r"^\s+(?:public\s+|protected\s+)?void\s+(\w+)\s*\(", line)
                    if mm:
                        results.append((path, mm.group(1)))
                    pending_test = False
                elif line.strip():
                    pending_test = False
        return results

    def test_naming_pattern(self) -> re.Pattern[str]:
        return _TEST_NAMING_PATTERN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    name = path.name
    # JUnit convention: FooTest.java, FooTests.java, FooTestCase.java
    if any(name.endswith(sfx) for sfx in _TEST_FILE_SUFFIXES):
        return True
    # TestFoo.java prefix convention
    if any(name.startswith(pfx) and name.endswith(".java") for pfx in _TEST_FILE_PREFIXES):
        return True
    return False


def _extract_throw_context(text: str, start: int, max_chars: int = 500) -> str:
    """Extract text from a throw statement through the matching closing paren.

    Walks forward from ``start`` tracking paren depth.  Stops at the matching
    close or ``max_chars``, whichever comes first.  Captures multi-line
    exception messages that may contain fix hints.
    """
    end = min(start + max_chars, len(text))
    depth = 0
    for i in range(start, end):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:end]


def _has_fix_hint(text: str, hint_marker: str) -> bool:
    lower = text.lower()
    if hint_marker and hint_marker.lower() in lower:
        return True
    for keyword in _FIX_HINT_KEYWORDS:
        if keyword in lower:
            return True
    return False


def _has_preceding_javadoc(lines: list[str], index: int) -> bool:
    """Return True if the nearest non-blank line above ``index`` closes a Javadoc block.

    A Javadoc block closes with ``*/`` on a line by itself (or ``*/`` as the
    last non-whitespace content).  Walks backwards from ``index - 1``,
    skipping blank lines.
    """
    j = index - 1
    while j >= 0:
        stripped = lines[j].strip()
        if stripped == "":
            j -= 1
            continue
        return stripped.endswith("*/")
    return False


JavaAdapter.count_file_loc = staticmethod(count_file_loc)  # type: ignore[attr-defined]
