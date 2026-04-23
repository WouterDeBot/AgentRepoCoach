"""Regex safety utilities — guards against ReDoS in user-configurable patterns.

User-supplied regex patterns (e.g. inline_ref_patterns, fixture_duplication_patterns)
are compiled and run against potentially large file contents.  A malicious or
misconfigured pattern with nested quantifiers can cause catastrophic backtracking.

This module provides ``safe_compile_pattern`` which rejects patterns containing
known-dangerous structures before they reach ``re.compile``.
"""
from __future__ import annotations

import re
import warnings

# Detect nested quantifiers: a quantifier (+ * {n,m}) applied to a group that
# itself contains a quantifier.  This is the most common source of catastrophic
# backtracking / ReDoS.
#
# Examples caught:  (a+)+  (x*)*  (a+)*  (x*)+  (\d+){2,}
# The pattern looks for:
#   (?:         — open non-capturing group for the "inner quantifier" context
#     [+*]      — a quantifier character
#     |         — or
#     \{[^}]*\} — a counted quantifier like {2,}
#   )
#   [^)]*       — optional stuff before the group closes
#   \)          — close of a capturing/non-capturing group
#   (?:         — followed by an outer quantifier
#     [+*?]     — single-char quantifier
#     |
#     \{[^}]*\} — counted quantifier
#   )
_NESTED_QUANTIFIER_RE = re.compile(
    r"""
    (?:                     # inner quantifier
        [+*]                #   single-char
      | \{ [^}]* \}        #   or counted {n,m}
    )
    [^)]*                   # stuff before group close
    \)                      # close group
    (?:                     # outer quantifier
        [+*?]               #   single-char
      | \{ [^}]* \}        #   or counted
    )
    """,
    re.VERBOSE,
)

_MAX_PATTERN_LENGTH = 500


def safe_compile_pattern(
    pattern: str,
    *,
    flags: int = 0,
) -> re.Pattern[str]:
    """Compile *pattern* after checking for known-dangerous regex structures.

    Raises ``ValueError`` if the pattern is rejected.  Emits a
    ``UserWarning`` for borderline cases.

    Parameters
    ----------
    pattern:
        Raw regex string from user configuration.
    flags:
        ``re`` flags forwarded to ``re.compile``.
    """
    if len(pattern) > _MAX_PATTERN_LENGTH:
        raise ValueError(
            f"Regex pattern is too long ({len(pattern)} chars, max {_MAX_PATTERN_LENGTH}). "
            "Simplify the pattern or split it into multiple entries."
        )

    if _NESTED_QUANTIFIER_RE.search(pattern):
        raise ValueError(
            f"Regex pattern contains nested quantifiers which can cause catastrophic "
            f"backtracking (ReDoS): {pattern!r}. Rewrite the pattern to avoid "
            f"constructs like (a+)+, (x*)+, (a+)*, etc."
        )

    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern {pattern!r}: {exc}") from exc

    # Warn on patterns that *might* be slow but aren't definitively dangerous.
    # Multiple adjacent quantifiers without nesting (e.g. a+b+c+) are usually
    # fine, but very long alternations inside quantified groups can be slow.
    if re.search(r"\([^)]*\|[^)]*\)[+*]", pattern):
        warnings.warn(
            f"Regex pattern {pattern!r} contains a quantified alternation group "
            f"which may be slow on large inputs. Consider anchoring or simplifying.",
            UserWarning,
            stacklevel=2,
        )

    return compiled
