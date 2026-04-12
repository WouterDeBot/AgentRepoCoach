---
layout: page
title: Configuration
permalink: /configuration/
---

# Configuration

AgentRepoCoach looks for `.agentrepocoach.toml` at the root of the scanned repo.
Every field is optional — the defaults are designed to produce a sensible
score on a zero-config Python or C# repo.

## Minimal example

```toml
# .agentrepocoach.toml
[weights]
navigability = 0.25
error_quality = 0.25
decision_queryability = 0.20
test_quality = 0.15
module_hygiene = 0.15
```

The five weights must sum to **1.0**; AgentRepoCoach refuses to run if they
don't. This is intentional — a silent drift would invalidate any
cross-repo comparison of scores.

## Full reference

```toml
[weights]
navigability = 0.25
error_quality = 0.25
decision_queryability = 0.20
test_quality = 0.15
module_hygiene = 0.15

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
```

## How the defaults were picked

- **Weights** (25/25/20/15/15): chosen heuristically to reward the two
  things that pay off first — navigation and actionable errors — while
  keeping test and module hygiene as non-trivial tiebreakers.
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
