"""AC-06 regression guard — bootstrap_signals.py must not contain shell-out or
exec-like calls that could execute scored repo content.

This test greps the source file for forbidden patterns and fails immediately
if any are found. It is intentionally simple so it can never be fooled by
obfuscation — a literal substring match is the right tool here.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

_FORBIDDEN_PATTERNS = (
    "subprocess",
    "os.system",
    "exec(",
    "eval(",
    "__import__",
)


def test_bootstrap_signals_has_no_forbidden_calls() -> None:
    """AC-06: bootstrap_signals.py must not contain shell-out or exec-like calls."""
    src_path = REPO_ROOT / "src" / "agentrepocoach" / "components" / "bootstrap_signals.py"
    assert src_path.is_file(), f"Source file not found: {src_path}"

    src = src_path.read_text(encoding="utf-8")
    for forbidden in _FORBIDDEN_PATTERNS:
        assert forbidden not in src, (
            f"AC-06 VIOLATION: {forbidden!r} found in bootstrap_signals.py. "
            "The scorer must not execute or shell out to any detected commands."
        )
