# Codebase Map

> Module-level guide to the AgentRepoCoach production code.

## Production package

### `agentrepocoach` (`src/agentrepocoach/`)

The single production package. Computes the Codebase Agent Health (CAH) score
for a repository by running six scoring components through a language adapter.

| Module | Purpose |
|--------|---------|
| `__init__.py` | Package root. Exports `compute_cah` and `VERSION`. |
| `__main__.py` | Enables `python -m agentrepocoach` invocation. |
| `cli.py` | Argument parser and CLI entry point (`main()`). |
| `compute.py` | Composite score orchestrator -- calls all six components. |
| `config.py` | TOML config loader, schema validation, dataclass models. |
| `scoring.py` | Shared scoring primitives (`scale_linear`, `file_mtime_age_days`). |
| `output.py` | Output formatters (JSON, Prometheus, Markdown) and coaching engine. |

### `agentrepocoach.adapters` (`src/agentrepocoach/adapters/`)

Language-specific scanning logic. One file per supported language.

| Module | Purpose |
|--------|---------|
| `base.py` | `LanguageAdapter` ABC, `ThrowSite`/`Declaration` dataclasses, file iteration helpers. |
| `__init__.py` | Adapter registry, `detect_primary()`, `get_adapter_by_name()`. |
| `csharp.py` | C# adapter (`.sln`/`.csproj` detection, `throw` scanning). |
| `python.py` | Python adapter (`pyproject.toml` detection, `raise` scanning). |
| `typescript.py` | TypeScript adapter (`package.json` detection, `throw` scanning). |
| `rust.py` | Rust adapter (`Cargo.toml` detection). |
| `go.py` | Go adapter (`go.mod` detection). |

### `agentrepocoach.components` (`src/agentrepocoach/components/`)

Six independent scoring components, each returning a 0-100 sub-score.

| Module | Component | What it measures |
|--------|-----------|-----------------|
| `documentation.py` | `navigability` | AGENTS.md, codebase map, CLI manifest, root cleanliness. |
| `error_quality.py` | `error_quality` | Fix-hint coverage, exception subclass ratio, generic dominance. |
| `decision_queryability.py` | `decision_queryability` | ADR catalog size, inline reference resolution. |
| `test_quality.py` | `test_quality` | Test naming conventions, helper files, fixture duplication. |
| `module_hygiene.py` | `module_hygiene` | Internal visibility, god files, doc coverage, architecture doc. |
| `bootstrap_signals.py` | `bootstrap_signals` | CI workflow presence (PR triggers) and README install/test commands. |

## Test package

### `tests/`

| Path | Purpose |
|------|---------|
| `conftest.py` | Pytest fixtures pointing to sample repos under `tests/fixtures/`. |
| `test_adapters.py` | Adapter detection, file discovery, and throw-site scanning tests. |
| `test_bootstrap_signals_security.py` | CI-Signal + README-quality scorer tests + AC-06 shell-out regression guard. |
| `test_cli.py` | CLI entry-point smoke tests (version, positional path, --all-languages). |
| `test_cli_compare.py` | CLI `compare` subcommand integration tests. |
| `test_components.py` | Component-level scoring tests against fixture repos. |
| `test_config.py` | Config loading, validation, and default-merging tests (incl. v1→v2 migration). |
| `test_multi_language.py` | Multi-language scoring with --all-languages flag. |
| `test_output.py` | Output formatters (JSON, Markdown, terminal). |
| `test_pr_bot.py` | PR bot module tests for structured score comparison. |
| `test_regex_safety.py` | ReDoS guard for user-configurable regex patterns. |
| `fixtures/` | Sample repos (C#, Python, TypeScript, Rust, Go) for integration tests. |
