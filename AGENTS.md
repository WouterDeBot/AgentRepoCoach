# AGENTS.md — AgentRepoCoach

> Entry point for AI coding agents working in this repository.

## Quick orientation

AgentRepoCoach computes the **Codebase Agent Health (CAH)** score: a 0-100
composite measuring how friendly a repository is for autonomous AI agents.
It ships as both a **Python CLI** and a **GitHub Actions composite action**.

- **Codebase map:** [docs/codebase-map.md](docs/codebase-map.md)
- **CLI manifest:** [docs/cli-manifest.json](docs/cli-manifest.json)
- **Architecture decisions:** [docs/adr/](docs/adr/)
- **Configuration:** [.agentrepocoach.toml](.agentrepocoach.toml)

## Build & test

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run the test suite
python -m pytest tests/ -v

# Type check
mypy src/

# Lint
ruff check src/ tests/
```

## Key entry points

| Path | Purpose |
|------|---------|
| `src/agentrepocoach/cli.py` | CLI entry point (`main()`) |
| `src/agentrepocoach/compute.py` | Composite score orchestrator |
| `src/agentrepocoach/adapters/` | Language adapters (one file per language) |
| `src/agentrepocoach/components/` | Five scoring components |
| `src/agentrepocoach/output.py` | Output formatters (JSON, Markdown, terminal) |
| `src/agentrepocoach/config.py` | TOML config loader |
| `action.yml` | GitHub Actions composite action definition |

## Adding a new language adapter

1. Copy `src/agentrepocoach/adapters/typescript.py` as a template
2. Implement all 9 `LanguageAdapter` abstract methods
3. Register the adapter in `src/agentrepocoach/adapters/__init__.py`
4. Create a fixture repo under `tests/fixtures/sample-<lang>-repo/`
5. Add tests in `tests/test_adapters.py`

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Constraints

- **Zero runtime dependencies** — stdlib only (Python 3.11+). This is a hard
  supply-chain-trust constraint. See [ADR-001](docs/adr/ADR-001-zero-dependencies.md).
- **No source code in output** — reports contain only counts, paths, and
  identifiers. See [ADR-002](docs/adr/ADR-002-no-source-in-output.md).
- **Regex-only analysis** — adapters use regex, not AST parsing.
  See [ADR-003](docs/adr/ADR-003-regex-only-analysis.md).
