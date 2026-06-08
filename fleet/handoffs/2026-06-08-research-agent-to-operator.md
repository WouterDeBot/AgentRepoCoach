---
type: research-finding
status: complete
from: research-agent
to: operator
created: 2026-06-08
---

# Research Report: AgentRepoCoach Codebase Survey for CLAUDE.md

## Summary

Full codebase read of AgentRepoCoach v0.4.1. 42 evidence-backed findings covering all 9
requested topic areas. Most important sharp edge: `bootstrap_signals` sub-components use
`"total"` as the max-points key while all other components use `"max"` — any code reading
sub-component dicts must use `sub.get("total", sub.get("max", 0))`.

## 1. Project Identity

- **What it does:** Computes a 0-100 "Codebase Agent Health (CAH)" composite score measuring how
  ready a repo is for autonomous AI agents, and coaches maintainers through fixes.
- **Target user:** Developers who want their repos to work well with AI coding agents.
- **Package name:** `agentrepocoach`
- **Current version:** `0.4.1` (must match in both `pyproject.toml` line 7 and
  `src/agentrepocoach/__init__.py` line 12 — these are the only two canonical locations)
- **PyPI install:** `pip install agentrepocoach`
- **Requires:** Python >= 3.11 (uses stdlib `tomllib` which ships in 3.11+)

Source: `pyproject.toml`, `src/agentrepocoach/__init__.py`

## 2. Repository Layout

```
src/agentrepocoach/          # Single production package (src-layout)
  __init__.py                # Exports compute_cah, VERSION
  __main__.py                # Enables python -m agentrepocoach
  cli.py                     # CLI entry point: main()
  compute.py                 # Composite orchestrator
  config.py                  # TOML config loader, schema, frozen dataclasses
  scoring.py                 # Shared primitives: scale_linear, file_mtime_age_days
  output.py                  # Formatters (JSON, Prometheus, Markdown) + coaching engine
  pr_bot.py                  # PR comparison: compare_scores, format_pr_comment
  regex_safety.py            # ReDoS guard for user-configurable patterns
  adapters/                  # Language adapters (one .py file per language)
    base.py                  # LanguageAdapter ABC, ThrowSite/Declaration dataclasses
    __init__.py              # _REGISTRY, detect_primary(), detect_all()
    csharp.py / python.py / typescript.py / rust.py / go.py
  components/                # Six scoring components
    __init__.py
    documentation.py         # navigability component (NOTE: filename != component name)
    error_quality.py
    decision_queryability.py
    test_quality.py
    module_hygiene.py
    bootstrap_signals.py     # Newest component (added v0.4.0)
tests/
  conftest.py                # Session-scoped pytest fixtures; calls _touch_recent_files()
  fixtures/                  # Synthetic sample repos — NOT collected by pytest
    sample-csharp-repo/      # Full-featured; used by dogfood.yml
    sample-python-repo/
    sample-typescript-repo/
    sample-go-repo/
    sample-rust-repo/
    sample-empty-repo/       # Tests NoAdapterError path
    sample-ci-signal-absent/
    sample-ci-signal-good/
    sample-ci-signal-no-pr/
    sample-readme-quality/
  test_adapters.py / test_bootstrap_signals_security.py / test_cli.py
  test_cli_compare.py / test_components.py / test_config.py
  test_multi_language.py / test_output.py / test_pr_bot.py / test_regex_safety.py
.github/workflows/
  ci.yml           # Main CI: tests on Python 3.11/3.12/3.13
  dogfood.yml      # End-to-end: runs action.yml against sample-csharp-repo
  cah-score.yml    # PR bot: posts score comparison comment on each PR
action.yml         # GitHub Actions composite action definition
pyproject.toml     # Package metadata, zero deps, dev extras
AGENTS.md          # AI agent entry point for this repo
docs/              # Jekyll site, ADRs, methodology, codebase-map.md, cli-manifest.json
fleet/             # Fleet Manager orchestration artifacts (not part of the package)
```

Source: directory walk; `docs/codebase-map.md`; `tests/conftest.py`

## 3. Build and Test Commands

```bash
# Editable install (dev mode)
pip install -e ".[dev]"

# Full test suite
python -m pytest tests/ -v
python -m pytest tests/ -q --tb=short   # CI style

# Single test file
python -m pytest tests/test_components.py -v

# Single test
python -m pytest tests/test_components.py::ClassName::test_name -v

# CLI after editable install
agentrepocoach .                                          # score cwd
agentrepocoach --repo /path/to/repo --verbose
python -m agentrepocoach.cli --repo tests/fixtures/sample-csharp-repo

# PyPI build
python -m build    # produces dist/*.whl and dist/*.tar.gz

# Type check / lint
mypy src/
ruff check src/ tests/
```

Source: `CONTRIBUTING.md`; `AGENTS.md`; `ci.yml`

## 4. Architecture

### CLI entry point

- Installed script: `agentrepocoach` → `agentrepocoach.cli:main` (`pyproject.toml` line 52)
- Module: `python -m agentrepocoach` → `src/agentrepocoach/__main__.py`
- Function: `main()` in `cli.py` line 152

### 6 scoring components and their sub-components

| Component (file) | Weight | Sub-components (pts each) |
|---|---:|---|
| `navigability` (`documentation.py`) | 22% | agents_md (30), codebase_map (30), cli_manifest (20), root_cleanliness (20) |
| `error_quality` (`error_quality.py`) | 22% | hint_coverage (50), exception_subclass_ratio (30), generic_exception_dominance (20) |
| `decision_queryability` | 18% | adr_catalog (60), inline_ref_resolution (40) |
| `test_quality` (`test_quality.py`) | 13% | naming_convention (40), helper_files (30), fixture_duplication (30) |
| `module_hygiene` (`module_hygiene.py`) | 13% | internal_visibility (30), god_files (30), doc_comment_coverage (20), architecture_doc (20) |
| `bootstrap_signals` | 12% | ci_signal (50), readme_quality (50) |

**Important:** The file `documentation.py` implements the `navigability` component. The
filename and component name do not match.

Source: `components/__init__.py` docstring; individual component files; `config.py` lines 33-40

### Adapter pattern

`LanguageAdapter` ABC in `adapters/base.py` requires 9 methods:
`detect`, `find_production_files`, `find_test_files`, `find_production_modules`,
`scan_throw_sites`, `generic_exception_names`, `scan_declarations`,
`find_test_methods`, `test_naming_pattern`.

5 adapters in `_REGISTRY`: `csharp`, `python`, `typescript`, `rust`, `go`.

All analysis is regex-based — no AST parsing. This is ADR-003.

Detection signals per adapter:
- Python: `pyproject.toml` → 1.0, `setup.py` → 0.9, any `.py` → 0.6
- Go: `go.mod` → 1.0, `*.go` at root/one-level → 0.5
- Rust: `Cargo.toml` → 1.0
- C#: `.sln` or `.csproj` → high confidence
- TypeScript: `tsconfig.json` or `package.json`

Tiebreaker when two adapters tie on confidence: higher production file count wins.

Source: `adapters/__init__.py`; `adapters/python.py` lines 59-66; `adapters/go.py` lines 72-79

### `--all-languages` mode

Uses `detect_all()`: includes adapter only when `confidence >= 0.5` AND `file_count >= 3`.
Returns multi-language shape (schema_version 2) with top-level `"languages"` dict.
Top-level `"total"` and `"language"` keys are absent in this shape.

Source: `compute.py` lines 93-142; `adapters/__init__.py` lines 65-88

### PR bot

- `compare` subcommand: `cli.py` lines 94-149 — reads two JSON files, prints delta table
- `pr_bot.py`: `parse_score_output`, `compare_scores`, `format_pr_comment`
- `cah-score.yml`: scores PR + base branch, posts/updates PR comment using
  `<!-- agentrepocoach -->` marker for idempotent updates

Source: `pr_bot.py`; `cli.py` lines 94-149; `.github/workflows/cah-score.yml`

### Schema version system

`CURRENT_SCHEMA_VERSION = 2` in `config.py` line 26.

- v1 had 5 components; v2 added `bootstrap_signals` (v0.4.0)
- version > current → `ConfigError`
- version < current → stderr warning + auto-normalizes weights by dividing by sum
- Missing in config → treated as current

Source: `config.py` lines 22-31, 218-231

## 5. Key Conventions and Constraints

### Zero runtime dependencies

`pyproject.toml` line 41: `dependencies = []`. Hard constraint — stdlib only. Uses
`tomllib` (stdlib 3.11+). This is why Python 3.11+ is required. ADR-001.

Source: `pyproject.toml` lines 39-41; `CONTRIBUTING.md` line 68

### Language detection priority

1. `--language` flag or `language =` in config → direct adapter lookup
2. `language = "auto"` (default) → `detect_primary()`: highest `(confidence, file_count)`

Source: `compute.py` lines 82-86; `cli.py` lines 199-203

### `readme_head_lines`

Default: `100`. Set in `BootstrapSignalsConfig` in `config.py` line 160.
Controls lines of README scanned for install/test commands.
Configurable: `[bootstrap_signals] readme_head_lines = N` in `.agentrepocoach.toml`.

Source: `config.py` line 160; `bootstrap_signals.py` line 161

### Config file parsing

- File: `<repo>/.agentrepocoach.toml`
- Parser: `tomllib.load()` on binary-mode handle (`"rb"`) — required by tomllib API
- Missing file → `Config()` defaults (no error)
- Malformed file → `ConfigError` (caught `tomllib.TOMLDecodeError`)
- `Config` is a frozen dataclass — use `dataclasses.replace()` to modify

Source: `config.py` lines 196-213; `cli.py` lines 200-202

### Test fixture mtime gotcha

`conftest.py` calls `_touch_recent_files()` on every fixture path at session start,
refreshing mtime on `docs/cli-manifest.json` and `docs/architecture.md`. Without this,
freshness-based sub-scores (`cli_manifest`, `architecture_doc`) return 0 on cold git clones.
If bypassing pytest fixtures in tests, call `_touch_recent_files()` manually.

Source: `tests/conftest.py` lines 59-68

### VERSION and pyproject.toml must always match

Two canonical locations — both must be bumped together on every release:
1. `pyproject.toml` line 7
2. `src/agentrepocoach/__init__.py` line 12

No `__version__` dunder is used anywhere else.

Source: `fleet/memory/software-engineer-learnings.md`

## 6. Release Process

Order matters — this exact sequence was documented after v0.3.0:

1. Bump version in `pyproject.toml` AND `src/agentrepocoach/__init__.py` (same commit)
2. Update `CHANGELOG.md` (move `[Unreleased]` items, update comparison links at bottom)
3. Commit the version-bump commit
4. `rm -rf dist/ && python -m build`
5. `twine upload dist/*`
6. `git tag vX.Y.Z` — tag must be on the version-bump commit, tag name must match pyproject version
7. `git push && git push --tags`
8. `gh release create vX.Y.Z`

PyPI upload happens before GitHub release so the package exists when GH release links to it.

Source: `fleet/memory/software-engineer-learnings.md` lines 9-11

## 7. Scoring Model

### Weights (defaults, schema v2)

```
CAH = 0.22 * navigability
    + 0.22 * error_quality
    + 0.18 * decision_queryability
    + 0.13 * test_quality
    + 0.13 * module_hygiene
    + 0.12 * bootstrap_signals
```

Weights must sum to 1.0 ± 0.01 or `ConfigError`. Customizable via `[weights]` in
`.agentrepocoach.toml` — but all 6 components must be present.

### Score interpretation

- 0-100 scale; each component is independently 0-100 before weighting
- Weights are heuristic, not empirically derived (documented in `docs/scoring.md` lines 92-93)
- Dogfood gate uses `fail-threshold: 50` — below 50 is considered failing
- 100/100 requires: all doc files present and fresh, all throw sites hinted + typed,
  20+ valid ADRs, 100% test naming coverage, CI with PR trigger, README with fenced
  install + test commands in first 100 lines

Source: `config.py` lines 33-40; `docs/scoring.md`; `dogfood.yml` line 44

## 8. GitHub Actions / CI

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | push/PR to main | pytest on Python 3.11/3.12/3.13 matrix + smoke test |
| `dogfood.yml` | push/PR to main | pytest on 3.11 + run composite action on sample-csharp-repo |
| `cah-score.yml` | PR to main | score PR + base, post/update comparison comment |

`action.yml` is a composite action (not Docker/JS). Uses `pip install -e .` inside the
action, so it always uses the action's own source, not PyPI.

Source: `.github/workflows/ci.yml`; `.github/workflows/dogfood.yml`;
`.github/workflows/cah-score.yml`; `action.yml`

## 9. Known Limitations and Gotchas

### `--all-languages` silently ignores flags

`_run_all_languages()` in `cli.py` lines 264-306 silently ignores:
`--compare`, `--prometheus`, `--comment`, `--verbose`, `--format markdown`,
`--format both`. Only `--format json` and `--json` are honored.

### Two max-key conventions in sub-component dicts (SHARP EDGE)

`bootstrap_signals` sub-component dicts use `"total"` as the max-points key:
```python
{"score": 30, "total": 50, ...}    # bootstrap_signals style
```
All other components use `"max"`:
```python
{"score": 28, "max": 30, ...}      # everyone else
```
This caused the v0.4.1 `--verbose` bug (CHANGELOG line 14).

**Always use the fallback pattern:**
```python
maximum = sub.get("total", sub.get("max", 0))
```
This is what `output.py` line 363 does after the v0.4.1 fix.

### Python adapter: production file scan is `src/`-first

`PythonAdapter.find_production_files()` only walks `src/` and `lib/`, or falls back to
top-level `__init__.py` packages at root. Arbitrary `.py` files in non-standard locations
are not found even when `detect()` returns high confidence.

Source: `adapters/python.py` lines 96-113

### ReDoS guard on user patterns

User patterns in `inline_ref_patterns` and `fixture_duplication_patterns` must pass
`safe_compile_pattern()`. Nested quantifiers → rejected + `UserWarning` emitted + pattern
skipped (not fatal). Max pattern length: 500 chars.

Source: `regex_safety.py`

### `docs/cli-manifest.json` freshness scoring

Uses file mtime: ≤7 days = full 20 pts, ≤14 days = 10 pts, older = 0 pts. Then halved
if `command_count < 20`. Cold git clones score 0 unless mtime is explicitly refreshed.

Source: `documentation.py` lines 158-171

### `Config` is a frozen dataclass

Direct attribute assignment on a `Config` instance raises `FrozenInstanceError`.
Use `dataclasses.replace(config, field=value)`.

Source: `config.py` line 83; `cli.py` lines 200-202

## Open Questions

1. **PAT-009 source file**: Referenced in the research request but no file named `PAT-009`
   exists in the repo. The rule ("tag on version-bump commit, pyproject version must match
   tag") is documented in `fleet/memory/software-engineer-learnings.md` but not in a
   standalone PAT-009 document.

2. **TypeScript and Rust detection thresholds**: Exact confidence scores were not confirmed
   from source (only Python and Go were fully read).

3. **What score constitutes "good"**: No documented guidance beyond the dogfood gate (50).
   The scoring docs show 82.47 as an example of a healthy repo.

STATUS: complete
