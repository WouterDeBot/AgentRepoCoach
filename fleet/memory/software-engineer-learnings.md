# Software Engineer Learnings

## Session Learnings

| Date | Category | Learning | Context |
|------|----------|---------|---------|
| 2026-04-23 | codebase | User-configurable regex patterns in AgentRepoCoach (inline_ref_patterns, fixture_duplication_patterns) flow through `re.compile` and `finditer`/`findall` against large file contents -- any new config-driven regex must use `safe_compile_pattern` from `regex_safety.py` | EXP-008 ReDoS mitigation |
| 2026-04-23 | methodology | Heuristic regex-on-regex detection of nested quantifiers is effective for common ReDoS patterns but cannot catch all exotic vectors; a wall-clock timeout approach would be more complete but adds runtime complexity | EXP-008 design trade-off |
| 2026-04-23 | codebase | output.py write_* functions take a Path and write to disk; when stdout output is needed, use the corresponding render_* functions (render_json, render_markdown_comment, render_prometheus) which return strings | EXP-010 --format stdout fix |
| 2026-04-23 | methodology | For release prep tasks, always verify version string locations via grep before bumping -- pyproject.toml and __init__.py VERSION are the two canonical locations in this project; no __version__ dunder is used | STR-003 v0.3.0 release prep |
| 2026-04-23 | methodology | PyPI publish flow: clean dist/, build, twine upload, tag, push tag, push main, gh release create -- this exact order ensures PyPI has the package before the GitHub release links to it; twine credentials persist via ~/.pypirc from prior releases | STR-003 v0.3.0 publish |
| 2026-05-23 | codebase | PythonAdapter.find_production_files() only walks src/ and lib/ dirs (or top-level __init__.py packages); .py files in arbitrary dirs are not found by production-file scan even when detect() returns high confidence. Test fixtures for multi-language repos must place Python files under src/. | XPL-003 multi-language tests |
| 2026-05-23 | codebase | Broad `except Exception` in CLI route handlers should be narrowed to the concrete exceptions the called function raises; compute_cah_all() surfaces NoAdapterError (RuntimeError subclass) — catching only (NoAdapterError, RuntimeError) is the correct tightened scope | XPL-003 except Exception anti-pattern |
| 2026-05-23 | methodology | When resuming a stream-idled SE, read the full diff (git diff) on all three modified files before touching anything — the prior agent may have completed implementation correctly; the resume task is often just tests + commit + PR, not re-implementation | XPL-003 resume protocol |
| 2026-06-08 | codebase | When a rebase produces a conflict on a docs file where the branch has the "right" version, use `git checkout --theirs <file> && git add <file>` then `git rebase --continue` rather than manually resolving conflict markers — faster and avoids Write-tool refusal on files with conflict markers | docs/cah-methodology rebase |
| 2026-06-08 | codebase | In AgentRepoCoach, bootstrap_signals sub-component dicts use "total" as the max-points key (not "max" like all other components) — any code reading sub-component dicts must use `sub.get("total", sub.get("max", 0))` | CLAUDE.md dual max-key convention |
