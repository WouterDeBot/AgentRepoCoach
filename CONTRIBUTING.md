# Contributing to AgentRepoCoach

Thanks for your interest in making AgentRepoCoach better. This guide covers the
short path from clone to merged PR.

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md).
By participating, you agree to uphold it.

## Development setup

```bash
git clone https://github.com/WouterDeBot/agentrepocoach.git
cd agentrepocoach
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

AgentRepoCoach targets Python 3.11+ and has zero runtime dependencies (stdlib
only, including `tomllib`). The `dev` extra installs `pytest`, `pytest-cov`,
`mypy`, and `ruff` for local development.

## Running tests

```bash
python -m pytest tests/ -v
```

The test suite runs in under a second because it uses tiny synthetic fixture
repos under `tests/fixtures/`. All new behavior must ship with tests.

## Smoke-testing the CLI

```bash
python -m agentrepocoach.cli --repo tests/fixtures/sample-csharp-repo
python -m agentrepocoach.cli --repo tests/fixtures/sample-python-repo --verbose
```

## Adding a new language adapter

Each supported language is a single class under `src/agentrepocoach/adapters/`
implementing the `LanguageAdapter` ABC defined in
`src/agentrepocoach/adapters/base.py`. To add (for example) Kotlin support:

1. Copy one of the stub adapters (`typescript.py`, `rust.py`, or `go.py`)
   to `kotlin.py` and rename the class to `KotlinAdapter`.
2. Implement the nine required methods on the base class:
   `detect`, `find_production_modules`, `find_production_files`,
   `find_test_files`, `scan_throw_sites`, `scan_declarations`,
   `find_test_methods`, `test_naming_pattern`, `generic_exception_names`.
3. Register the adapter in `src/agentrepocoach/adapters/__init__.py` so
   `detect_primary` can find it.
4. Add at least one fixture repo under `tests/fixtures/sample-kotlin-repo/`
   and cover it with tests in `tests/test_adapters.py` and
   `tests/test_components.py`.
5. Update the "Languages supported" table in `README.md`.

The five component scorers under `src/agentrepocoach/components/` only interact
with the adapter contract — they do not know about any specific language.
A well-implemented adapter gets all five components "for free".

## Style conventions

- Type hints on every public function.
- Prefer frozen dataclasses for config records.
- Early returns, small functions, no magic numbers.
- No third-party runtime dependencies. Ever. Stdlib or it does not ship.
- Regexes must be anchored (`\b...\b`) and free of catastrophic backtracking.
- Output writers must never emit code snippets or raw message bodies — only
  counts, percentages, type names, and file paths.

## Pull request process

1. Fork the repo and create a feature branch from `main`.
2. Add or update tests for the change.
3. Run `python -m pytest tests/ -v` and confirm green.
4. Open a PR with a clear title and a short "what changed / why" body.
5. The CI dogfood workflow must pass before review.
6. Squash-merge is the default.

## Reporting bugs

Please include the AgentRepoCoach version, Python version, the language adapter
being used, and a minimal reproducer. Use the bug-report issue template.

## Methodology changes

Changes to the CAH scoring formula (weights, sub-components, thresholds)
require a methodology discussion first — open an issue using the feature
request template before submitting code. See `docs/METHODOLOGY.md` for the
current specification.
