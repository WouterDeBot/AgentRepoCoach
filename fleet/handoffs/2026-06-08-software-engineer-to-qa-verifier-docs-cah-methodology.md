---
type: implementation
status: complete
from: fe-software-engineer
to: fe-qa-verifier
created: 2026-06-08
commit: bea19f28e7685226e3d19f8eaff87003e855f9ef
build_status: pass
tests_added: 0
files_changed:
  - docs/METHODOLOGY.md
---

## Summary

Rebased `docs/cah-methodology` branch onto `origin/main` (was 8 commits behind)
and updated `docs/METHODOLOGY.md` to reflect schema v2 (6 components, v0.4.0
weights).

## What was implemented

### Rebase
- `git rebase origin/main` — one conflict on `docs/METHODOLOGY.md`
- Resolved by taking the branch's detailed version (`git checkout --theirs`)
- Continued rebase cleanly; no further conflicts
- Force-pushed: `git push --force-with-lease origin docs/cah-methodology`

### Schema v2 fixes applied (commit `bea19f2`)

1. **Composite formula** — updated from v1 (`0.25/0.25/0.20/0.15/0.15`) to v2
   (`0.22/0.22/0.18/0.13/0.13/0.12`) with `bootstrap_signals` as the sixth term

2. **Source citations corrected**:
   - `config.py:33-40` (default weights dict, verified against actual file)
   - `compute.py:51-53` (weighted summation loop)
   - `config.py:262-271` (weight validation function)

3. **Weight rationale text** — "The 25/25/20/15/15 split" → "The 22/22/18/13/13/12
   split"; added paragraph explaining bootstrap_signals at 12% as structural
   prerequisite added in v0.4.0

4. **Per-component headings** — all updated to v2 pts (25→22, 25→22, 20→18,
   15→13, 15→13)

5. **§6 Bootstrap signals (12 pts)** — full new section added after §5 Module
   hygiene, containing:
   - WHY for agents narrative (agent can't verify changes without runnable tests)
   - Sub-component table with line citations from `bootstrap_signals.py`
     - `ci_signal` (50 pts): L20, L56-89
     - `readme_quality` (50 pts): L21, L116-179
   - `"total"` vs `"max"` max-points key gotcha (per CLAUDE.md)
   - Calibration notes (configurable globs, PR-trigger patterns, readme_head_lines)
   - Limitations (regex-not-semantic, fenced-only, byte-cap DoS guard)

6. **Worked example** — updated to 6-component v2 weights; total still ~68
   (realistic example kept intact)

7. **"five structural properties"** → **"six"** in "How to read a score" section

8. **Stray `STATUS: complete` line** removed from end of doc (fleet metadata
   that leaked into the branch)

### What was NOT changed
- `README.md` — already has `## Methodology` section linking to the doc
  (from `0beb94d` commit on the branch)
- The two "five" occurrences in the bootstrap_signals section
  ("the other five components score") are intentionally correct — they
  describe bootstrap_signals as a prerequisite for the *other* five

## Test coverage

Docs-only change. No code was modified.

Full pytest suite run:
```
python3 -m pytest tests/ -q
169 passed in 0.41s
```

## Design deviations

None. All fixes applied exactly as specified in the task brief.

## Branch state at handoff

- Branch: `docs/cah-methodology`
- Tip: `bea19f28e7685226e3d19f8eaff87003e855f9ef`
- Rebased onto: `cc3c41e` (origin/main HEAD)
- Remote: pushed to `origin/docs/cah-methodology`
- HEAD at SE turn-end: `main` (cc3c41e)

## Acceptance criteria verification

- [x] Formula matches config.py default weights exactly (6 components, v2)
- [x] bootstrap_signals §6 section present with sub-component table and line citations
- [x] Worked example uses v2 weights
- [x] No references to "five components" remain (the two "other five" usages are correct)
- [x] README.md has the "Methodology" link section (from branch commit 0beb94d)
- [x] Branch is up to date with main (rebased)
- [x] `python3 -m pytest tests/ -q` passes (169 passed)

STATUS: complete
