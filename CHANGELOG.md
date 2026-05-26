# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2026-05-26

### Added

- **CI-Signal scorer** (`bootstrap_signals` component, 50 pts): detects whether the repo defines
  a runnable CI workflow (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`).
  Awards 30 pts for any workflow file, +20 pts when a workflow triggers on `pull_request`.
  Configurable via `[bootstrap_signals.ci_workflow_globs]` for non-mainstream CI providers.
- **README-quality scorer** (`bootstrap_signals` component, 50 pts): detects whether the
  README's first 100 lines contain both an install command (`pip install`, `npm install`,
  `cargo`, `go install`, `dotnet add`, etc.) and a test command (`pytest`, `npm test`,
  `go test`, `cargo test`, `dotnet test`, etc.) in fenced code blocks. Configurable via
  `[bootstrap_signals.install_command_patterns]` and `[bootstrap_signals.test_command_patterns]`.
- **`bootstrap_signals` component**: new 6th top-level component (12% default weight) bundling
  the two scorers above. Option B per design — visible in the score breakdown table.
- **Config schema v2**: `CURRENT_SCHEMA_VERSION` bumped from 1 to 2. Existing `.agentrepocoach.toml`
  files must add `schema_version = 2` and `bootstrap_signals = 0.12` to `[weights]`.
  See `docs/configuration.md` for the one-line migration recipe.
- **8 new tests** covering CI-signal (absent, no-PR-trigger, with-PR-trigger), README-quality
  (absent, install-only, full), config migration (v1 raises with recipe, v2 defaults), and
  an AC-06 grep regression guard preventing shell-out calls in `bootstrap_signals.py`.

### Changed

- **Default weights rebalanced** to accommodate the new 6th component (sum remains 1.0):
  - `navigability`: 0.25 → 0.22
  - `error_quality`: 0.25 → 0.22
  - `decision_queryability`: 0.20 → 0.18
  - `test_quality`: 0.15 → 0.13
  - `module_hygiene`: 0.15 → 0.13
  - `bootstrap_signals`: new at 0.12

### Security

- README reads capped at 200 KB and 100 lines before any pattern matching (DoS guard).
- CI workflow scans short-circuit at 50 files per glob pattern.
- No shell-out, no eval, no exec — enforced via AC-06 grep regression test.

## [0.3.1] — 2026-05-24

### Fixed

- **Release integrity:** `--all-languages` flag was merged after v0.3.0 published to PyPI; v0.3.1 ships the flag to PyPI users
- `--language` help text was stale (`csharp|python|auto`); now reflects the full registered adapter set (`csharp|go|python|rust|typescript|auto`)

### Improved

- `agentrepocoach .` (positional path) now works; matches industry convention (`ruff .`, `mypy .`)

## [0.3.0] — 2026-04-23

### Added

- `compare` CLI subcommand for local score file comparison (base vs. PR JSON reports)
- PR bot module (`pr_bot.py`) for structured score comparison on pull requests
- `--compare` flag on the default `score` command for inline baseline comparison
- GitHub Actions workflow for automated PR score comments (`cah-score.yml`)
- GitHub Actions CI pipeline with Python 3.11/3.12/3.13 test matrix (`ci.yml`)
- CLI integration tests (`test_cli_compare.py`)

### Fixed

- Language detection priority when multiple adapters tie on confidence — tiebreaker now uses production file count to select the dominant language deterministically

### Security

- ReDoS regex safety guard (`regex_safety.py`) for user-configurable patterns — detects nested quantifiers before compilation to prevent catastrophic backtracking

## [0.2.0] — 2026-04-23

### Added

- Full TypeScript language adapter — `tsconfig.json`/`package.json` detection, throw-site scanning with multi-line context, JSDoc detection, Jest/Vitest test method extraction
- Full Go language adapter — `go.mod` detection, `errors.New`/`fmt.Errorf`/custom error mapping, Go doc comment detection, `Test*` function extraction
- Full Rust language adapter — `Cargo.toml` detection, `panic!`/`Err(Custom)` mapping, `///` doc comment detection, `#[test]` attribute detection
- Coaching recommendations engine — analyzes sub-component score gaps, surfaces top-3 actionable fix tips ranked by weighted impact; available in terminal summary, verbose output, markdown PR comments, and JSON report (new `coaching` array)
- `AGENTS.md` codebase navigation file
- `codebase-map.md` for agent-friendly repo overview
- `cli-manifest.json` for CLI discoverability
- Five Architecture Decision Records (ADRs)
- Fix hints on all raise sites; docstrings on all public declarations

### Fixed

- Python adapter `_TEST_METHOD_PATTERN` was missing `re.MULTILINE` flag, causing zero test methods to be detected

## [0.1.0] — 2026-04-12

### Added

- Initial public release of AgentRepoCoach
- 5-component composite codebase-agent-health scoring: error_quality, module_hygiene, decision_queryability, test_quality, documentation
- Composite GitHub Action (composite type, setup-python based)
- Python CLI with `--repo`, `--config`, `--format`, `--output`, `--version` flags
- TOML configuration via `.agentrepocoach.toml` (stdlib `tomllib`, no PyYAML dependency)
- Language adapters for C# and Python (full); stubs for TypeScript, Rust, Go
- JSON and Markdown output formats
- Three example workflow files: basic-scoring, pr-gate, scheduled-report
- Jekyll documentation site under `docs/`
- Comprehensive test suite with synthetic fixture repos (35 tests)

### Security

- Symlink traversal guard
- Large file OOM ceiling (10 MB skip)
- Regex ReDoS audit (informal — formal audit deferred to v0.2)
- JSON output contains no source code snippets, only counts, paths, and identifiers

[Unreleased]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/WouterDeBot/agentrepocoach/releases/tag/v0.1.0
