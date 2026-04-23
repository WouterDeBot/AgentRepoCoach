---
id: ADR-004
status: accepted
date: 2025-02-01
---

# ADR-004: Composite GitHub Action over Docker action

## Context

AgentRepoCoach ships as a GitHub Action for CI integration. Two packaging
strategies were evaluated:

1. **Docker action** -- bundles a container image with all dependencies. Slower
   cold start (~30s to pull), but fully isolated.
2. **Composite action** -- runs steps directly on the runner using
   `actions/setup-python`. Faster (~5s setup), reuses runner's Python, and
   keeps the action definition in a single `action.yml` file.

## Decision

Use a **composite action** defined in `action.yml`. The action installs
AgentRepoCoach via pip into the runner's Python environment and invokes the
CLI directly.

## Consequences

- No Dockerfile to maintain; `action.yml` is the single source of truth.
- The action depends on `actions/setup-python` being available on the runner.
- Self-hosted runners without Python 3.11+ will fail; the action's
  `python-version` input defaults to `3.11`.
- Future: if the tool gains compiled extensions (violating ADR-001), this
  decision must be revisited.
