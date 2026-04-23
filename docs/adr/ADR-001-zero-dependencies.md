---
id: ADR-001
status: accepted
date: 2025-01-15
---

# ADR-001: Zero runtime dependencies

## Context

AgentRepoCoach runs inside CI pipelines and developer machines. Adding runtime
dependencies (PyYAML, toml, requests, etc.) increases supply-chain attack
surface and installation friction. The tool must be trustworthy enough to run
on any codebase without review concerns.

## Decision

The project will have **zero runtime dependencies** -- stdlib only (Python
3.11+). TOML parsing uses the built-in `tomllib` module. File I/O, regex, JSON,
and `dataclasses` cover every need.

Dev dependencies (pytest, mypy, ruff) are permitted because they never execute
in production.

## Consequences

- No third-party TOML library -- `tomllib` is read-only, which is sufficient
  since the tool never writes config files.
- No YAML support for config -- TOML was chosen partly because it has stdlib
  support in 3.11+.
- Any future feature requiring HTTP, templating, or AST parsing must find a
  stdlib-only path or be rejected.
- Minimum Python version is pinned to 3.11 (for `tomllib`).
