# AgentRepoCoach

> Score your codebase on how ready it is for AI agents — and coach you through the fixes.

[![PyPI version](https://img.shields.io/pypi/v/agentrepocoach.svg)](https://pypi.org/project/agentrepocoach/)
[![License](https://img.shields.io/github/license/WouterDeBot/agentrepocoach.svg)](./LICENSE)
[![CI](https://github.com/WouterDeBot/agentrepocoach/actions/workflows/ci.yml/badge.svg)](https://github.com/WouterDeBot/agentrepocoach/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/agentrepocoach.svg)](https://pypi.org/project/agentrepocoach/)

AgentRepoCoach computes the **Codebase Agent Health (CAH)** score: a single 0-100
composite measuring how friendly a repository is for autonomous AI agents.
It blends six statically-measurable components:

- **Navigability** (22%) — `AGENTS.md`, codebase map, CLI manifest, root cleanliness
- **Error quality** (22%) — fix-hint coverage, exception typing, generic-exception dominance
- **Decision queryability** (18%) — ADR catalog, inline reference resolution
- **Test quality** (13%) — naming convention, helper presence, fixture duplication
- **Module hygiene** (13%) — internal visibility, god files, doc coverage, architecture doc freshness
- **Bootstrap signals** (12%) — CI-Signal (runnable test workflow on PR triggers) + README-quality (install + test commands in first 100 lines)

AgentRepoCoach ships with zero runtime dependencies — it uses the Python 3.11+
standard library only, including `tomllib` for config parsing.

## Usage as a GitHub Action

Add this to any workflow to score your repo and fail the build if the
composite score drops below a threshold:

```yaml
name: codebase-health

on:
  push:
    branches: [main]
  pull_request:

jobs:
  agentrepocoach:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run AgentRepoCoach
        id: agentrepocoach
        uses: WouterDeBot/agentrepocoach@v1
        with:
          repo-path: .
          output-format: json
          output-path: ./agentrepocoach-report.json
          fail-threshold: '70'

      - name: Show composite score
        run: echo "Score: ${{ steps.agentrepocoach.outputs.composite-score }}"

      - uses: actions/upload-artifact@v4
        with:
          name: agentrepocoach-report
          path: ./agentrepocoach-report.json
```

**Action inputs:**

| Input            | Default                    | Description |
|------------------|----------------------------|-------------|
| `repo-path`      | `.`                        | Path to scan |
| `config-path`    | `.agentrepocoach.toml`          | TOML config file |
| `output-format`  | `json`                     | `json`, `markdown`, or `both` |
| `output-path`    | `./agentrepocoach-report.json`  | Where to write the report |
| `fail-threshold` | (unset)                    | Exit 1 if score < threshold |
| `python-version` | `3.11`                     | Python version to install |

**Action outputs:**

| Output            | Description |
|-------------------|-------------|
| `composite-score` | CAH composite score (0-100) |
| `report-path`     | Absolute path to written report |

## Usage as a CLI

Install and run:

```bash
pip install agentrepocoach
```

Run tests after contributing:

```bash
pytest tests/ -q
```

Score your repository:

```bash
# Score the current directory (prints a summary table)
python -m agentrepocoach.cli --repo .

# Write a JSON report to disk
python -m agentrepocoach.cli --repo . --format json --output ./report.json

# Per-sub-component breakdown
python -m agentrepocoach.cli --repo . --verbose

# Compare against a baseline report (inline delta)
python -m agentrepocoach.cli --repo . --format json --output ./pr.json --compare ./baseline.json

# Compare two saved score files
python -m agentrepocoach.cli compare ./baseline.json ./pr.json

# Show the installed version
python -m agentrepocoach.cli --version
```

## Configuration

AgentRepoCoach looks for `.agentrepocoach.toml` at the repo root. Every field is
optional — the tool ships with sensible defaults and will score zero-config
repos without complaint.

Minimal example (schema v2, required since v0.4.0):

```toml
# .agentrepocoach.toml
schema_version = 2

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12

[paths]
adr_dir = "docs/adr/"
architecture_doc = "docs/architecture.md"

[error_quality]
domain_exception_types = ["DomainError", "ValidationError"]

[decision_queryability]
inline_ref_patterns = ["ADR-\\d+"]

# Optional: tune bootstrap_signals detection globs / patterns
[bootstrap_signals]
ci_workflow_globs = [".github/workflows/*.yml", ".gitlab-ci.yml"]
```

**Migrating from v1?** Add `schema_version = 2` at the top and add
`bootstrap_signals = 0.12` to `[weights]`, then rebalance the other five
weights so they still sum to 1.0. See [`docs/configuration.md`](docs/configuration.md)
for the one-line migration recipe.

See [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the full config schema
and scoring formula.

## Languages supported

| Language      | Status                | Notes |
|---------------|-----------------------|-------|
| C#            | Full MVP              | Throw-site scanner, XML doc detection, internal visibility, .sln/.csproj discovery |
| Python        | Full MVP              | Raise-site scanner, docstring detection, top-level visibility, src/ layout aware |
| TypeScript    | Full MVP              | Throw-site scanner with multi-line context, JSDoc detection, Jest/Vitest test extraction |
| Rust          | Full MVP              | `panic!`/`Err(Custom)` mapping, `///` doc comment detection, `#[test]` attribute detection |
| Go            | Full MVP              | `errors.New`/`fmt.Errorf`/custom error mapping, Go doc comment detection, `Test*` function extraction |

Adding a new adapter is a small, well-scoped task — see
[`CONTRIBUTING.md`](CONTRIBUTING.md#adding-a-new-language-adapter).

## Coaching recommendations

When you run AgentRepoCoach, it doesn't just score your repo — it tells you
what to fix first. The coaching engine analyzes sub-component score gaps and
surfaces the top-3 actionable tips ranked by weighted impact. Recommendations
appear in:

- Terminal summary (default output)
- Verbose mode (`--verbose`)
- Markdown PR comments (`--format markdown`)
- JSON reports (`--format json`, new `coaching` array)

## How it works

AgentRepoCoach detects the primary language of the repo, loads a language
adapter, and runs six component scorers against the adapter's view of
the codebase. Each component returns a 0-100 sub-score with a transparent
breakdown. The weighted sum is the composite CAH score.

The six components are:

- **Navigability** — checks for `AGENTS.md`, codebase map, CLI manifest, and root cleanliness.
- **Error quality** — scores fix-hint coverage, exception typing, and generic-exception usage.
- **Decision queryability** — audits ADR catalog completeness and inline ADR cross-references.
- **Test quality** — checks test naming conventions, helper presence, and fixture duplication.
- **Module hygiene** — inspects internal visibility ratios, god files, doc coverage, and architecture doc freshness.
- **Bootstrap signals** — language-agnostic CI-Signal scorer (does the repo have a CI workflow triggered on pull requests?) and README-quality scorer (do the first 100 README lines contain both an install and a test command in fenced code blocks?). Both are configurable via `[bootstrap_signals]` in `.agentrepocoach.toml`.

Every output field is a count, percentage, type name, or file path —
AgentRepoCoach never emits code snippets or raw message bodies, so reports
are safe to publish as CI artifacts.

## License

Apache 2.0. See [LICENSE](LICENSE).
