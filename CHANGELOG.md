# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Jekyll documentation site under `docs-site/`
- Comprehensive test suite with synthetic fixture repos (35 tests)

### Security

- Symlink traversal guard
- Large file OOM ceiling (10 MB skip)
- Regex ReDoS audit (informal — formal audit deferred to v0.2)
- JSON output contains no source code snippets, only counts, paths, and identifiers

[Unreleased]: https://github.com/WouterDeBot/agentrepocoach/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/WouterDeBot/agentrepocoach/releases/tag/v0.1.0
