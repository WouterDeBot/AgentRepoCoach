"""Tests for the regex safety guard (ReDoS mitigation)."""
from __future__ import annotations

import re
import warnings

import pytest

from agentrepocoach.regex_safety import safe_compile_pattern


# --- Valid patterns pass through ---


class TestValidPatterns:
    """safe_compile_pattern must accept well-formed, safe patterns."""

    @pytest.mark.parametrize(
        "pattern",
        [
            r"ADR-\d+",
            r"\bADR-\d+\b",
            r"TODO|FIXME",
            r"[A-Z]{2,4}-\d{1,5}",
            r"new\s+Builder\(",
            r"\.build\(\)",
        ],
    )
    def test_safe_patterns_compile(self, pattern: str) -> None:
        result = safe_compile_pattern(pattern)
        assert isinstance(result, re.Pattern)

    def test_flags_forwarded(self) -> None:
        pat = safe_compile_pattern(r"hello", flags=re.IGNORECASE)
        assert pat.flags & re.IGNORECASE


# --- Dangerous patterns are rejected ---


class TestDangerousPatterns:
    """Nested quantifiers must be rejected with ValueError."""

    @pytest.mark.parametrize(
        "pattern,description",
        [
            (r"(a+)+", "plus-inside-plus"),
            (r"(a*)*", "star-inside-star"),
            (r"(a+)*", "plus-inside-star"),
            (r"(a*)+", "star-inside-plus"),
            (r"(\d+){2,}", "plus-inside-counted"),
            (r"(x+y+)+", "multiple-plus-inside-plus"),
            (r"([a-z]+)+", "char-class-plus-inside-plus"),
        ],
    )
    def test_nested_quantifier_rejected(self, pattern: str, description: str) -> None:
        with pytest.raises(ValueError, match="nested quantifiers"):
            safe_compile_pattern(pattern)

    def test_invalid_regex_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid regex"):
            safe_compile_pattern(r"(unclosed")

    def test_too_long_pattern_rejected(self) -> None:
        long_pattern = r"a" * 501
        with pytest.raises(ValueError, match="too long"):
            safe_compile_pattern(long_pattern)


# --- Warning on borderline patterns ---


class TestBorderlinePatterns:
    """Quantified alternation groups should warn but not reject."""

    def test_quantified_alternation_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = safe_compile_pattern(r"(foo|bar)+")
            assert isinstance(result, re.Pattern)
            assert len(w) == 1
            assert "quantified alternation" in str(w[0].message)
