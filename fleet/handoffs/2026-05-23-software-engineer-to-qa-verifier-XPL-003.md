---
type: implementation
status: complete
from: fe-software-engineer
to: fe-qa-verifier
created: 2026-05-23
milestone: XPL-003
commit: 083bfb8f99529ed0adf98e7fe75d681f443353a1
build_status: pass
tests_added: 14
files_changed:
  - src/agentrepocoach/adapters/__init__.py
  - src/agentrepocoach/cli.py
  - src/agentrepocoach/compute.py
  - tests/test_multi_language.py
---

# Implementation Report: XPL-003 MVP — Multi-Language Scoring (--all-languages flag)

## What Was Implemented

This is a RESUME run. The prior `fe-software-engineer` completed the implementation
of three source files before stream-idling. This run:
1. Verified the prior implementation against the locked scope.
2. Patched a minor issue (broad `except Exception`).
3. Added 14 new tests.
4. Ran backward compat verification (Phase D).
5. Committed and opened PR #3.

### Source files modified

| File | Change |
|------|--------|
| `src/agentrepocoach/adapters/__init__.py` | Added `_collect_candidates()` helper + `detect_all()` with threshold `confidence >= 0.5 AND file_count >= 3`. Refactored `detect_primary()` to reuse `_collect_candidates()`. |
| `src/agentrepocoach/cli.py` | Added `--all-languages` flag (mutually exclusive with `--language`) via `add_mutually_exclusive_group()`. Added `_run_all_languages()` route handler. Fixed IMP-003: `--language` help text updated from stale `csharp|python|auto` to `csharp|go|python|rust|typescript|auto`. |
| `src/agentrepocoach/compute.py` | Added `compute_cah_all()` returning `{"schema_version": 2, "generator": ..., "languages": {lang: per-lang-result}}`. No top-level `"total"` or `"language"` keys. |

### Test file created

| File | Tests |
|------|-------|
| `tests/test_multi_language.py` | 14 tests across 4 classes (AC-1 threshold edges, AC-2 positive, AC-3 empty, AC-4 JSON shape) |

## Phase A — Scope Compliance Verdict

All locked scope items are correctly implemented:
- `detect_all()` exists with threshold `confidence >= 0.5 AND file_count >= 3`. PASS.
- `--all-languages` flag present, mutually exclusive with `--language`. PASS.
- `compute_cah_all()` returns `{"languages": {...}}` nested shape. PASS.
- No top-level `"total"` or `"language"` in `--all-languages` output. PASS.
- `schema_version` bumped to 2 for multi-language shape only (config stays v1). PASS.
- IMP-003: `--language` help text corrected. PASS.

**Patch applied:** `except Exception` in `_run_all_languages()` tightened to
`except (NoAdapterError, RuntimeError)` — the only exceptions `compute_cah_all()` surfaces.

## Phase B — Existing Test Suite

- **122 tests passed** before any changes. 0 failures.

## Phase C — New Tests

- **14 new tests** in `tests/test_multi_language.py`
- **136 total** after additions (0 regressions)

Test classes:
- `TestDetectAllThresholdEdgeCases` (4 tests) — confidence 0.49 excluded, 0.50 included; file_count 2 excluded, 3 included.
- `TestDetectAllPositive` (2 tests) — mixed Python+Go fixture; sorted order.
- `TestDetectAllEmpty` (2 tests) — empty repo and below-threshold repo both return `[]`.
- `TestComputeCahAllShape` (6 tests) — no top-level `total`/`language`; `languages` dict present; sub-shape; `schema_version == 2`; empty-repo returns `{}`.

## Phase D — Backward Compat

Verified using project root as fixture (Python: confidence=1.0, 22 production files).

**Without `--all-languages` (v0.3 shape):**
```
schema_version: 1, total: 89.62, language: python
```
Top-level `"total"` and `"language"` present. PASS.

**With `--all-languages` (new shape):**
```
schema_version: 2, languages: {python: {...}}
```
No top-level `"total"` or `"language"`. PASS.

## Phase E — Commit + PR

- Commit SHA: `083bfb8f99529ed0adf98e7fe75d681f443353a1`
- PR: https://github.com/WouterDeBot/AgentRepoCoach/pull/3

## Design Deviations

None. Implementation follows the locked scope exactly.

## Known Limitations / Operator Notes

- The `--all-languages` path does NOT support `--compare`, `--prometheus`, `--comment`, `--verbose`, or `--format markdown/both`. These silently do nothing if passed with `--all-languages`. The format handling for `--format json` IS implemented. This is consistent with the scope deferred items list.
- Only `python` is detected in the project root (this project is pure Python). A true multi-language test requires constructing a temp fixture or pointing at a repo that contains both, e.g., a Python + Go project.
- The installed package at the system Python path predates these changes — always run with `PYTHONPATH=src` or `pip install -e .` in dev.

## Deferred Items (from scoping doc)

- `pr_bot.py` multi-language support
- `.github/workflows/cah-score.yml` `--all-languages` mode
- Aggregate rollup score across all detected languages
- Markdown output format for multi-language shape
- Per-language config overrides
- Prometheus metrics for multi-language shape

STATUS: complete
