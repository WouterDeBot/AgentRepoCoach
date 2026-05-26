# Architecture

> High-level overview of how AgentRepoCoach computes the CAH score.

## System overview

AgentRepoCoach is a single-process, zero-dependency Python CLI that scores a
repository's readiness for AI coding agents. The tool reads files from disk
(never modifies them), computes six component scores, and emits a weighted
composite score in JSON, Markdown, or Prometheus format.

## Data flow

```
Repository on disk
       |
       v
  +-----------+       +------------------+
  | CLI       | ----> | Config Loader    |  reads .agentrepocoach.toml
  | (cli.py)  |       | (config.py)      |
  +-----------+       +------------------+
       |                       |
       v                       v
  +-----------+       +------------------+
  | Compute   | <---- | Language Adapter  |  auto-detected or forced
  | Orchestr. |       | (adapters/*.py)   |
  | (compute) |       +------------------+
  +-----------+
       |
       +--- calls each component with (repo_root, config, adapter) --->
       |
       |    +-- navigability (documentation.py)
       |    +-- error_quality (error_quality.py)
       |    +-- decision_queryability (decision_queryability.py)
       |    +-- test_quality (test_quality.py)
       |    +-- module_hygiene (module_hygiene.py)
       |    +-- bootstrap_signals (bootstrap_signals.py)
       |
       v
  +-----------+
  | Output    |  JSON / Markdown / Prometheus / terminal
  | (output)  |
  +-----------+
```

## Module responsibilities

### `cli.py`
Parses command-line arguments, loads config, picks the adapter, calls
`compute_cah()`, and dispatches to output writers. Returns exit code 0 on
success, 2 on user errors.

### `compute.py`
The composite orchestrator. Calls all six component functions, applies
config-driven weights, and assembles the final result dict. Also invokes the
coaching engine to generate improvement recommendations.

### `config.py`
Loads `.agentrepocoach.toml` using stdlib `tomllib`. All fields are optional
with research-validated defaults. Frozen dataclasses enforce immutability.

### `adapters/`
Each adapter implements the 9-method `LanguageAdapter` interface (ADR-005).
Adapters handle file discovery, throw-site scanning, declaration scanning,
and test-method detection using regex-only analysis (ADR-003).

### `components/`
Six pure-function modules. Each receives `(repo_root, config, adapter)` and
returns `{"score": float, "total": 100, "breakdown": {...}}`. Components
never import each other -- they communicate only through the orchestrator.

### `scoring.py`
Two shared primitives: `scale_linear()` for clamped interpolation and
`file_mtime_age_days()` for freshness checks.

### `output.py`
Four output writers (JSON, Prometheus, Markdown PR comment, terminal summary)
plus the coaching recommendation engine. Output never contains source code
(ADR-002).

## Key constraints

- **Zero runtime dependencies** (ADR-001): stdlib only, Python 3.11+.
- **No source in output** (ADR-002): only counts, percentages, and paths.
- **Regex-only analysis** (ADR-003): no AST parser libraries.
- **Composite GitHub Action** (ADR-004): runs via `action.yml`, not Docker.
