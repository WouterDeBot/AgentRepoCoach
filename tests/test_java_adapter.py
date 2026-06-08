"""Tests for the Java language adapter against the sample-java-repo fixture."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agentrepocoach.adapters import JavaAdapter, detect_primary
from agentrepocoach.adapters.java import _is_test_file

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
JAVA_FIXTURE = FIXTURES_ROOT / "sample-java-repo"
PYTHON_FIXTURE = FIXTURES_ROOT / "sample-python-repo"


@pytest.fixture(scope="session")
def java_fixture() -> Path:
    """Path to the sample Java fixture repo."""
    return JAVA_FIXTURE


@pytest.fixture(scope="session")
def adapter() -> JavaAdapter:
    return JavaAdapter()


# ---------------------------------------------------------------------------
# AC-03 / test 1: detection via pom.xml
# ---------------------------------------------------------------------------


def test_detect_by_pom_xml(adapter: JavaAdapter, java_fixture: Path) -> None:
    """detect() returns 1.0 when pom.xml is present at the repo root."""
    score = adapter.detect(java_fixture)
    assert score == 1.0


# ---------------------------------------------------------------------------
# test 2: detection via build.gradle
# ---------------------------------------------------------------------------


def test_detect_by_gradle(adapter: JavaAdapter, tmp_path: Path) -> None:
    """detect() returns 1.0 when build.gradle is present."""
    (tmp_path / "build.gradle").write_text("// gradle build file\n")
    score = adapter.detect(tmp_path)
    assert score == 1.0


# ---------------------------------------------------------------------------
# test 3: detection via .java files only (no build file)
# ---------------------------------------------------------------------------


def test_detect_by_java_files(adapter: JavaAdapter, tmp_path: Path) -> None:
    """detect() returns 0.8 when only .java files are present (no build descriptor)."""
    (tmp_path / "Foo.java").write_text("public class Foo {}\n")
    score = adapter.detect(tmp_path)
    assert score == 0.8


# ---------------------------------------------------------------------------
# test 4: detection returns 0.0 for a Python repo
# ---------------------------------------------------------------------------


def test_detect_returns_zero_for_python_repo(adapter: JavaAdapter) -> None:
    """detect() returns 0.0 on a repo with no Java artefacts."""
    score = adapter.detect(PYTHON_FIXTURE)
    assert score == 0.0


# ---------------------------------------------------------------------------
# AC-04 / test 5: ThrowSite scanning detects throw sites
# ---------------------------------------------------------------------------


def test_throw_sites_detected(adapter: JavaAdapter, java_fixture: Path) -> None:
    """ThrowSite count is >= 3 — App.java has 1 throw, UserService.java has 2."""
    prod_files = adapter.find_production_files(java_fixture)
    sites = adapter.scan_throw_sites(prod_files, hint_marker="", domain_exception_types=set())
    assert len(sites) >= 3, f"Expected >= 3 throw sites, got {len(sites)}: {sites}"


# ---------------------------------------------------------------------------
# test 6: fix-hint detection on DataException messages in UserService.java
# ---------------------------------------------------------------------------


def test_fix_hint_detection(adapter: JavaAdapter, java_fixture: Path) -> None:
    """At least one ThrowSite has has_fix_hint=True (UserService uses 'Suggested fix:')."""
    prod_files = adapter.find_production_files(java_fixture)
    sites = adapter.scan_throw_sites(prod_files, hint_marker="", domain_exception_types=set())
    hinted = [s for s in sites if s.has_fix_hint]
    assert len(hinted) >= 1, (
        f"Expected at least one ThrowSite with has_fix_hint=True, got 0. Sites: {sites}"
    )


# ---------------------------------------------------------------------------
# test 7: declarations are found for public methods and classes
# ---------------------------------------------------------------------------


def test_declarations_found(adapter: JavaAdapter, java_fixture: Path) -> None:
    """scan_declarations() returns declarations for public methods/classes."""
    prod_files = adapter.find_production_files(java_fixture)
    decls = adapter.scan_declarations(prod_files)
    names = {d.name for d in decls}
    # App.java has class App + methods greet, main
    # UserService.java has class UserService + methods createUser, deleteUser, getDisplayName
    # DataException.java has class DataException + constructors
    assert "App" in names, f"Expected 'App' in declarations, got {names}"
    assert "UserService" in names, f"Expected 'UserService' in declarations, got {names}"
    # At least one method declaration
    method_names = {"greet", "createUser", "deleteUser", "getDisplayName", "main"}
    assert names & method_names, f"Expected at least one method declaration, got {names}"


# ---------------------------------------------------------------------------
# test 8: test files detected
# ---------------------------------------------------------------------------


def test_test_files_detected(adapter: JavaAdapter, java_fixture: Path) -> None:
    """AppTest.java is detected as a test file."""
    test_files = adapter.find_test_files(java_fixture)
    test_names = {f.name for f in test_files}
    assert "AppTest.java" in test_names, (
        f"Expected AppTest.java in test files, got {test_names}"
    )


# ---------------------------------------------------------------------------
# test 9: compute_cah returns a non-zero score
# ---------------------------------------------------------------------------


def test_compute_cah_nonzero(java_fixture: Path) -> None:
    """compute_cah(fixture_path) returns a composite score > 0."""
    from agentrepocoach.compute import compute_cah
    result = compute_cah(java_fixture)
    score_key = "score" if "score" in result else "total"
    assert result[score_key] > 0, f"Expected CAH score > 0, got {result}"


# ---------------------------------------------------------------------------
# test 10: end-to-end CLI with --language java
# ---------------------------------------------------------------------------


def test_e2e_language_flag(java_fixture: Path) -> None:
    """CLI exits 0 and prints a CAH score when --language java is supplied."""
    result = subprocess.run(
        [sys.executable, "-m", "agentrepocoach", str(java_fixture), "--language", "java"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"CLI exited {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The output should contain a numeric CAH score.
    assert any(char.isdigit() for char in result.stdout), (
        f"Expected numeric CAH score in stdout, got: {result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Additional unit: _is_test_file helper covers naming conventions
# ---------------------------------------------------------------------------


def test_is_test_file_recognises_conventions() -> None:
    """_is_test_file returns True for *Test.java, Test*.java, *Tests.java."""
    assert _is_test_file(Path("FooTest.java"))
    assert _is_test_file(Path("FooTests.java"))
    assert _is_test_file(Path("FooTestCase.java"))
    assert _is_test_file(Path("TestFoo.java"))
    assert not _is_test_file(Path("Foo.java"))
    assert not _is_test_file(Path("App.java"))


# ---------------------------------------------------------------------------
# Additional unit: detect_primary selects java for the java fixture
# ---------------------------------------------------------------------------


def test_detect_primary_picks_java(java_fixture: Path) -> None:
    """detect_primary() selects the Java adapter for the Java fixture."""
    adapter = detect_primary(java_fixture)
    assert adapter.name == "java"
