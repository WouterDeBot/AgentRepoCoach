# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/WouterDeBot/agentrepocoach/releases/tag/v0.1.0
