---
type: code
status: review
from: software-engineer
to: qa-verifier
created: 2026-04-23
milestone: EXP-008
---

# Implementation Report: Regex Complexity Guard (EXP-008)

## Summary

Added a regex safety utility that rejects user-configurable patterns containing nested quantifiers (ReDoS vectors) before they reach `re.compile`. Applied the guard to both user-facing regex config points identified in the security audit (XPL-002, findings F-05 and F-06).

## Files Created

| File | Description |
|------|-------------|
| `src/agentrepocoach/regex_safety.py` | `safe_compile_pattern()` utility -- rejects nested quantifiers, length-caps patterns, warns on borderline constructs |
| `tests/test_regex_safety.py` | 17 tests covering safe/dangerous/borderline patterns |

## Files Modified

| File | Change |
|------|--------|
| `src/agentrepocoach/components/decision_queryability.py` | `_compile_inline_ref_patterns` now uses `safe_compile_pattern` instead of raw `re.compile`; emits `warnings.warn` on rejection |
| `src/agentrepocoach/components/test_quality.py` | `_score_fixture_duplication` now uses `safe_compile_pattern` instead of raw `re.compile`; emits `warnings.warn` on rejection |

## Test Coverage

- **17 new tests** in `tests/test_regex_safety.py`
  - 7 parametrized: valid/safe patterns compile successfully
  - 7 parametrized: dangerous nested-quantifier patterns rejected with `ValueError`
  - 1: invalid regex syntax rejected
  - 1: overly long patterns rejected
  - 1: borderline quantified-alternation patterns warn but compile
- **111 total tests pass** (94 existing + 17 new), 0 regressions

## Design Deviations

None. The implementation follows the specified approach (heuristic detection of nested quantifiers, `ValueError` on rejection, `warnings.warn` on borderline cases).

## Known Limitations

- The nested-quantifier heuristic is structural (regex-on-regex), not a full formal analysis. Exotic ReDoS vectors that don't use nested quantifiers (e.g., very long alternation chains) are warned but not blocked.
- The 500-char length cap is a pragmatic guard, not a theoretical limit.
