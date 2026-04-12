"""Go adapter stub.

Detects the language via ``go.mod`` but raises :class:`NotSupportedError` for
every analysis method. Contributors: copy this file to add real Go support.
See ``docs/METHODOLOGY.md`` for the contract each method must satisfy.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .base import Declaration, LanguageAdapter, NotSupportedError, ThrowSite


class GoAdapter(LanguageAdapter):
    name = "go"

    def detect(self, repo_path: Path) -> float:
        if (repo_path / "go.mod").is_file():
            return 0.3
        return 0.0

    def find_production_files(self, repo_path: Path) -> list[Path]:
        raise NotSupportedError(_message())

    def find_test_files(self, repo_path: Path) -> list[Path]:
        raise NotSupportedError(_message())

    def find_production_modules(self, repo_path: Path) -> list[str]:
        raise NotSupportedError(_message())

    def scan_throw_sites(
        self,
        files: Iterable[Path],
        hint_marker: str,
        domain_exception_types: set[str],
    ) -> list[ThrowSite]:
        raise NotSupportedError(_message())

    def generic_exception_names(self) -> set[str]:
        raise NotSupportedError(_message())

    def scan_declarations(self, files: Iterable[Path]) -> list[Declaration]:
        raise NotSupportedError(_message())

    def find_test_methods(self, files: Iterable[Path]) -> list[tuple[Path, str]]:
        raise NotSupportedError(_message())

    def test_naming_pattern(self) -> re.Pattern[str]:
        raise NotSupportedError(_message())


def _message() -> str:
    return (
        "Go support is not yet implemented. "
        "See docs/METHODOLOGY.md for the contributing guide."
    )
