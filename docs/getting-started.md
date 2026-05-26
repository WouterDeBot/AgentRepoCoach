---
layout: page
title: Getting Started
permalink: /getting-started/
---

# Getting Started

AgentRepoCoach runs in two places: as a GitHub Action in CI, and as a Python
CLI locally. Pick whichever matches how you work — the output is identical.

## Option A — GitHub Action (recommended)

Drop this file at `.github/workflows/agentrepocoach.yml`:

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

      - uses: WouterDeBot/agentrepocoach@v1
        id: agentrepocoach
        with:
          repo-path: .
          fail-threshold: '70'

      - run: echo "Score: ${{ steps.agentrepocoach.outputs.composite-score }}"
```

On the next push, the job prints the composite score. Set `fail-threshold`
to an integer and the workflow will exit 1 when the score drops below it.

## Option B — Python CLI

AgentRepoCoach targets Python 3.11+ (it uses `tomllib` from the stdlib).

```bash
pip install agentrepocoach

# Score the current directory (positional path — matches ruff/mypy convention)
agentrepocoach .
# or equivalently:
python -m agentrepocoach.cli --repo .

# Write a JSON report
python -m agentrepocoach.cli --repo . --format json --output ./report.json

# Per-sub-component breakdown
python -m agentrepocoach.cli --repo . --verbose

# Score all detected languages in a multi-language repo
python -m agentrepocoach.cli --repo . --all-languages

# Show the installed version
python -m agentrepocoach.cli --version
```

## Reading the output

Every run produces a composite score and six component scores:

```
AgentRepoCoach report — repo at .
==============================
Total score:        82.47 / 100
  navigability         19.45 / 22.00
  error_quality        18.08 / 22.00
  decision_queryability 14.24 / 18.00
  test_quality         10.49 / 13.00
  module_hygiene       10.31 / 13.00
  bootstrap_signals    10.00 / 12.00
```

Pass `--verbose` to see the sub-components that feed each score.
Every number traces back to a file path, a percentage, or a count —
there are no hidden weights.

## First improvements to try

AgentRepoCoach is opinionated about a few easy wins. In our experience, the
fastest way to raise a score on an existing repo is:

1. **Write an `AGENTS.md`** at the repo root with links to your
   codebase map, CLI manifest, and ADR directory.
2. **Add fix hints to your exception messages.** A message like
   "Config file not found — create it at `./config.toml`" is worth 5x an
   "Invalid operation" message.
3. **Group decisions into ADRs.** Even a three-file `docs/adr/` directory
   scores better than 50 inline "TODO decision" comments.
4. **Stop using generic exceptions.** Define two or three domain types
   (`ValidationError`, `NotFoundError`) and route everything through them.

See [Scoring]({{ "/scoring" | relative_url }}) for the exact formula.

## What next?

- [Configuration]({{ "/configuration" | relative_url }}) — tune weights, thresholds, and paths.
- [FAQ]({{ "/faq" | relative_url }}) — troubleshooting and common questions.

AgentRepoCoach is licensed under **Apache 2.0**.
