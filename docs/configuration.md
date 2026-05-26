---
layout: page
title: Configuration
permalink: /configuration/
---

# Configuration

AgentRepoCoach looks for `.agentrepocoach.toml` at the root of the scanned repo.
Every field is optional — the defaults are designed to produce a sensible
score on a zero-config Python or C# repo.

## Schema version migration (v1 → v2)

AgentRepoCoach v0.4.0 introduces a 6th component (`bootstrap_signals`) and bumps
the config schema from v1 to v2. If you have an existing `.agentrepocoach.toml`
with `schema_version = 1`, you will see:

```
error: Unsupported schema_version 1. This tool requires schema_version 2.
To migrate from v1 to v2: set `schema_version = 2` in your .agentrepocoach.toml
and add `bootstrap_signals = 0.12` to the [weights] table ...
```

**One-line migration recipe:**

1. Change `schema_version = 1` to `schema_version = 2`.
2. Add `bootstrap_signals = 0.12` to the `[weights]` table.
3. Adjust the other five weights so they still sum to 1.0 (e.g. reduce each by 0.02–0.03).

Example v2 weights block:

```toml
schema_version = 2

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12
```

## Minimal example

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
```

The six weights must sum to **1.0**; AgentRepoCoach refuses to run if they
don't. This is intentional — a silent drift would invalidate any
cross-repo comparison of scores.

**From v0.4.0 onward, agentrepocoach soft-upgrades older configs:** if your
`.agentrepocoach.toml` still has `schema_version = 1`, the tool will print a
one-shot warning to stderr and continue loading. Your existing five weights are
proportionally rescaled so the new sixth component (`bootstrap_signals`) is
included at its default value and the total stays at 1.0. You can suppress the
warning by updating the file to `schema_version = 2` and explicitly rebalancing
the `[weights]` table as shown above. Future schema versions that the installed
tool does not recognise will still raise an error — you must upgrade the tool
in that case.

## Full reference

```toml
schema_version = 2

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12

[paths]
agents_md = "AGENTS.md"
codebase_map = "docs/codebase-map.md"
cli_manifest = "docs/cli-manifest.json"
adr_dir = "docs/adr/"
architecture_doc = "docs/architecture.md"

[navigability]
cli_manifest_min_commands = 5
cli_manifest_max_age_days = 7
root_allowlist = ["README.md", "LICENSE", "pyproject.toml", ".gitignore"]

[error_quality]
fix_hint_marker = "fix:"
domain_exception_types = ["DomainError", "ValidationError", "NotFoundError"]
generic_exception_ceiling = 0.20

[decision_queryability]
adr_min_count = 3
inline_ref_patterns = ["ADR-\\d+", "RFC-\\d+"]

[test_quality]
helper_min_count = 1
fixture_duplication_patterns = []

[module_hygiene]
god_file_loc_ceiling = 500
architecture_doc_max_age_days = 60

[bootstrap_signals]
# Glob patterns for CI workflow files. Add custom entries for Buildkite, Drone, etc.
ci_workflow_globs = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
]
# Install commands to detect in README fenced code blocks (first 100 lines).
install_command_patterns = [
    "pip install", "uv pip", "npm install", "npm ci",
    "yarn install", "cargo install", "cargo build",
    "go install", "go get", "dotnet add", "dotnet restore",
]
# Test commands to detect in README fenced code blocks (first 100 lines).
test_command_patterns = [
    "pytest", "npm test", "npm run test",
    "go test", "cargo test", "dotnet test",
    "make test", "mvn test", "gradle test",
]
# Number of README lines to scan. Increase if your install instructions appear later.
readme_head_lines = 100
```

## How the defaults were picked

- **Weights** (22/22/18/13/13/12): rebalanced in v2 to accommodate the 6th
  `bootstrap_signals` component while keeping navigability and error quality
  as the top priorities.
- **CLI manifest 7-day freshness window**: short enough to catch manifests
  that fell out of sync with the CLI, long enough to tolerate one week off.
- **Generic exception ceiling 20%**: in practice, well-typed codebases land
  below 10%; 20% is the "you have work to do but it isn't on fire" line.
- **God file LOC ceiling 500**: conservative; many teams pick 300 or 800.
  Tune it in your own config if your codebase has a different convention.
- **Architecture doc 60-day freshness**: long enough that weekly commits
  aren't forced, short enough that a once-a-year doc update will fail.

See [Scoring]({{ "/scoring" | relative_url }}) for how each field feeds
the components.

## Multi-language repos

AgentRepoCoach auto-detects the primary language by counting production files.
For a mixed repo (e.g. a C# backend with a TypeScript frontend), it scores
whichever language has the most production files. Multi-language scoring
is on the roadmap for v0.2.

## Stub adapters

TypeScript, Rust, and Go adapters exist but currently raise
`NotImplementedError`. If you run AgentRepoCoach against a repo whose primary
language is one of those, the CLI exits with a clear message. Pull
requests are welcome — see [Contributing]({{ "/contributing" | relative_url }}).

## Action inputs vs config file

A few fields are available as GitHub Action inputs as well as config
entries. When both are set, the **Action input wins** — this lets you
override the baked-in config from a workflow without editing files.

| Action input | Config field | Notes |
|---|---|---|
| `repo-path` | n/a | Relative to workspace |
| `config-path` | n/a | Defaults to `.agentrepocoach.toml` |
| `output-format` | n/a | `json`, `markdown`, or `both` |
| `output-path` | n/a | Where the report is written |
| `fail-threshold` | n/a | Exit 1 if composite score falls below |

---

AgentRepoCoach is licensed under **Apache 2.0**.
