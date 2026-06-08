---
type: code
status: review
from: software-engineer
to: qa-verifier
created: 2026-04-23
milestone: EXP-010
---

# Implementation Report: Fix CLI --format json stderr warning (EXP-010)

## Summary

Fixed the CLI so that `--format json` and `--format markdown` print formatted output directly to stdout when `--output` is not provided, instead of printing a confusing error message to stderr. `--format both` still requires `--output` since it writes two files.

## Files Modified

| File | Description |
|------|-------------|
| `src/agentrepocoach/output.py` | Added `render_json()`, `render_markdown_comment()`, and `render_prometheus()` string-returning variants of the existing `write_*` file-writing functions. Refactored `write_json` and `write_prometheus` to use the new render functions internally. |
| `src/agentrepocoach/cli.py` | Updated `--format` handling: when `--output` is omitted, `json`/`markdown` formats print to stdout via new `_print_formatted()` helper. Only `--format both` still errors without `--output`. Updated help text. Suppressed default summary when `--format` replaces stdout. |
| `tests/test_cli_compare.py` | Added `TestFormatWithoutOutput` class with 4 tests covering json-to-stdout, markdown-to-stdout, both-requires-output error, and json-with-output regression. |

## Test Coverage

- **Tests added:** 4
- **Total tests:** 122 (was 118)
- **All passing:** Yes
- **No regressions:** Confirmed

## Design Deviations

None. The fix follows the preferred approach from the task specification.

## Commit

`75ca796` - Fix --format json/markdown to print to stdout without requiring --output
