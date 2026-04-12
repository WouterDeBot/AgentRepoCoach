---
layout: home
title: AgentRepoCoach
description: Score your codebase on how ready it is for AI agents.
---

# AgentRepoCoach

> **Score your codebase on how ready it is for AI agents — and coach you through the fixes.**

AgentRepoCoach computes the **Codebase Agent Health (CAH)** score: a single 0-100
composite measuring how friendly a repository is for autonomous AI agents.
It runs as a GitHub Action or a CLI, has **zero runtime dependencies**, and
uses only the Python 3.11+ standard library.

## Why AgentRepoCoach?

AI coding agents spend a surprising amount of their context budget just
figuring out *where to look* in your repo. A repo with clear error messages,
explicit module boundaries, resolvable decision references, and a top-level
`AGENTS.md` lets an agent get productive in seconds instead of minutes.

AgentRepoCoach makes that quality measurable. Every field in its report is a
count, a percentage, or a path — never a code snippet — so reports are safe
to publish as CI artifacts.

## 60-second install (GitHub Action)

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
```

## Or install as a CLI

```bash
pip install agentrepocoach
python -m agentrepocoach.cli --repo . --verbose
```

## What gets scored?

AgentRepoCoach blends five statically-measurable components:

| Component | Weight | What it checks |
|---|---:|---|
| **Navigability** | 25% | `AGENTS.md`, codebase map, CLI manifest, root cleanliness |
| **Error quality** | 25% | Fix-hint coverage, domain exceptions, generic exception dominance |
| **Decision queryability** | 20% | ADR catalog, inline reference resolution |
| **Test quality** | 15% | Naming convention, helper presence, fixture duplication |
| **Module hygiene** | 15% | Internal visibility, god files, doc coverage, architecture doc freshness |

See [Scoring]({{ "/scoring" | relative_url }}) for the exact formula and
sub-component breakdown.

## Next steps

- [Getting started]({{ "/getting-started" | relative_url }}) — install, run, read the output
- [Configuration]({{ "/configuration" | relative_url }}) — `.agentrepocoach.toml` reference
- [Scoring]({{ "/scoring" | relative_url }}) — the 5 components and the composite formula
- [FAQ]({{ "/faq" | relative_url }}) — common questions
- [Contributing]({{ "/contributing" | relative_url }}) — adding a language adapter

AgentRepoCoach is licensed under **Apache 2.0**. See the [LICENSE](https://github.com/WouterDeBot/agentrepocoach/blob/main/LICENSE) file for details.
