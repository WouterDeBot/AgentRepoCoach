"""Shared pytest fixtures for the AgentRepoCoach test suite."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def csharp_fixture() -> Path:
    """Path to the sample C# fixture repo."""
    path = FIXTURES_ROOT / "sample-csharp-repo"
    _touch_recent_files(path)
    return path


@pytest.fixture(scope="session")
def python_fixture() -> Path:
    """Path to the sample Python fixture repo."""
    path = FIXTURES_ROOT / "sample-python-repo"
    _touch_recent_files(path)
    return path


@pytest.fixture(scope="session")
def empty_fixture() -> Path:
    """Path to the empty fixture repo (no supported language)."""
    return FIXTURES_ROOT / "sample-empty-repo"


def _touch_recent_files(repo_path: Path) -> None:
    """Refresh mtime on files whose freshness sub-scores matter in tests.

    Keeps ``docs/cli-manifest.json`` and ``docs/architecture.md`` fresh
    (<= 7 and <= 60 days respectively) regardless of when the fixture was
    checked out from git.
    """
    now = time.time()
    for rel in ("docs/cli-manifest.json", "docs/architecture.md"):
        target = repo_path / rel
        if target.is_file():
            os.utime(target, (now, now))
