"""Tests for multi-language scoring (detect_all, compute_cah_all, --all-languages flag).

Coverage maps to XPL-003-MVP acceptance criteria:
- AC-1: Threshold logic edge cases (confidence and file_count boundaries)
- AC-2: detect_all() positive — mixed-language fixture
- AC-3: detect_all() empty — nothing meets threshold
- AC-4: compute_cah_all() JSON shape contract
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from agentrepocoach.adapters import LanguageAdapter, PythonAdapter, detect_all
from agentrepocoach.compute import compute_cah_all, _MULTI_LANGUAGE_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers / mini-fixtures
# ---------------------------------------------------------------------------


def _make_python_repo(root: Path, file_count: int) -> Path:
    """Scaffold a minimal Python repo with ``file_count`` .py source files."""
    src = root / "src"
    src.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    for i in range(file_count):
        (src / f"module_{i}.py").write_text(f"def func_{i}(): pass\n")
    return root


# ---------------------------------------------------------------------------
# AC-1: Threshold logic edge cases
# ---------------------------------------------------------------------------


class TestDetectAllThresholdEdgeCases:
    """Confidence and file_count boundary conditions (AC-1)."""

    def test_confidence_below_floor_excluded(self, tmp_path: Path) -> None:
        """Adapter with confidence=0.49 must be excluded."""
        repo = _make_python_repo(tmp_path / "repo", file_count=5)
        adapter = PythonAdapter()
        with patch.object(type(adapter), "detect", return_value=0.49):
            with patch("agentrepocoach.adapters._REGISTRY", {"python": lambda: adapter}):
                result = detect_all(repo)
        assert result == []

    def test_confidence_at_floor_included(self, tmp_path: Path) -> None:
        """Adapter with confidence=0.50 and file_count>=3 must be included."""
        repo = _make_python_repo(tmp_path / "repo", file_count=5)
        adapter = PythonAdapter()
        with patch.object(type(adapter), "detect", return_value=0.50):
            with patch("agentrepocoach.adapters._REGISTRY", {"python": lambda: adapter}):
                result = detect_all(repo)
        assert len(result) == 1
        assert result[0][0] == pytest.approx(0.50)

    def test_file_count_below_floor_excluded(self, tmp_path: Path) -> None:
        """Adapter with file_count=2 (< 3) must be excluded even at confidence=1.0."""
        repo = _make_python_repo(tmp_path / "repo", file_count=2)
        # PythonAdapter.detect() will return 1.0 (pyproject.toml present)
        # but only 2 production files exist → excluded
        result = detect_all(repo)
        assert result == []

    def test_file_count_at_floor_included(self, tmp_path: Path) -> None:
        """Adapter with file_count=3 and confidence>=0.5 must be included."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = detect_all(repo)
        assert len(result) == 1
        assert result[0][1].name == "python"


# ---------------------------------------------------------------------------
# AC-2: detect_all() positive — multiple languages above threshold
# ---------------------------------------------------------------------------


class TestDetectAllPositive:
    """detect_all() returns multiple adapters when the repo is multi-language (AC-2)."""

    def test_detect_all_returns_multiple_adapters(self, tmp_path: Path) -> None:
        """A repo with Python AND Go source files above threshold returns both adapters.

        PythonAdapter.find_production_files() looks in ``src/`` or ``lib/`` dirs.
        GoAdapter.find_production_files() looks for ``*.go`` files.
        """
        repo = tmp_path / "mixed"
        repo.mkdir()

        # Python side: pyproject.toml + 3 .py files under src/
        (repo / "pyproject.toml").write_text("[project]\nname = 'mixed'\n")
        py_src = repo / "src"
        py_src.mkdir()
        for i in range(3):
            (py_src / f"module_{i}.py").write_text(f"def func_{i}(): pass\n")

        # Go side: go.mod + 3 .go files
        (repo / "go.mod").write_text("module example.com/mixed\ngo 1.21\n")
        go_src = repo / "go_src"
        go_src.mkdir()
        for i in range(3):
            (go_src / f"pkg{i}.go").write_text(f"package main\nfunc F{i}() {{}}\n")

        result = detect_all(repo)
        adapter_names = {adapter.name for _, adapter in result}
        assert "python" in adapter_names
        assert "go" in adapter_names

    def test_detect_all_sorted_by_confidence_descending(self, tmp_path: Path) -> None:
        """Results are sorted confidence-descending."""
        repo = _make_python_repo(tmp_path / "repo", file_count=5)
        result = detect_all(repo)
        # At least one result (python) must be present
        assert result
        confidences = [c for c, _ in result]
        assert confidences == sorted(confidences, reverse=True)


# ---------------------------------------------------------------------------
# AC-3: detect_all() empty — no language meets threshold
# ---------------------------------------------------------------------------


class TestDetectAllEmpty:
    """detect_all() returns [] when nothing meets the detection threshold (AC-3)."""

    def test_empty_repo_returns_empty_list(self, tmp_path: Path) -> None:
        """A repo with no recognised language files returns []."""
        empty = tmp_path / "empty"
        empty.mkdir()
        result = detect_all(empty)
        assert result == []

    def test_below_file_count_threshold_returns_empty_list(self, tmp_path: Path) -> None:
        """A Python repo with only 2 production files (< 3) returns []."""
        repo = _make_python_repo(tmp_path / "repo", file_count=2)
        result = detect_all(repo)
        assert result == []


# ---------------------------------------------------------------------------
# AC-4: compute_cah_all() JSON shape contract
# ---------------------------------------------------------------------------


class TestComputeCahAllShape:
    """compute_cah_all() output shape: no top-level total/language, nested languages dict (AC-4)."""

    def test_no_top_level_total(self, tmp_path: Path) -> None:
        """Top-level 'total' key must be absent from multi-language output."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = compute_cah_all(repo)
        assert "total" not in result

    def test_no_top_level_language(self, tmp_path: Path) -> None:
        """Top-level 'language' key must be absent from multi-language output."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = compute_cah_all(repo)
        assert "language" not in result

    def test_languages_dict_present(self, tmp_path: Path) -> None:
        """Top-level 'languages' dict is present and non-empty for a qualifying repo."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = compute_cah_all(repo)
        assert "languages" in result
        assert isinstance(result["languages"], dict)
        assert len(result["languages"]) >= 1

    def test_languages_sub_shape(self, tmp_path: Path) -> None:
        """Each language entry has 'total' and 'language' sub-keys."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = compute_cah_all(repo)
        for lang_name, lang_result in result["languages"].items():
            assert "total" in lang_result, f"{lang_name} missing 'total'"
            assert "language" in lang_result, f"{lang_name} missing 'language'"
            assert lang_result["language"] == lang_name

    def test_schema_version_is_bumped(self, tmp_path: Path) -> None:
        """schema_version must be the multi-language version (2), not the v0.3 value (1)."""
        repo = _make_python_repo(tmp_path / "repo", file_count=3)
        result = compute_cah_all(repo)
        assert result["schema_version"] == _MULTI_LANGUAGE_SCHEMA_VERSION
        assert result["schema_version"] == 2

    def test_empty_repo_returns_empty_languages(self, tmp_path: Path) -> None:
        """When no language meets threshold, 'languages' is an empty dict."""
        empty = tmp_path / "empty"
        empty.mkdir()
        result = compute_cah_all(empty)
        assert result["languages"] == {}
        assert "total" not in result
