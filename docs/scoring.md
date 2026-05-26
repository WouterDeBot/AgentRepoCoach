---
layout: page
title: Scoring
permalink: /scoring/
---

# Scoring

AgentRepoCoach produces a **Codebase Agent Health (CAH)** composite score on a
0-100 scale. It blends six components, each independently scored 0-100,
with weights that sum to 1.0.

## The composite formula

```
CAH = 0.22 * navigability
    + 0.22 * error_quality
    + 0.18 * decision_queryability
    + 0.13 * test_quality
    + 0.13 * module_hygiene
    + 0.12 * bootstrap_signals
```

Every component returns a number between 0 and 100. The weighted sum
lands on the same 0-100 scale, which makes CAH directly comparable
across repos and over time.

## Component 1 — Navigability (22%)

**Question:** How easily does an AI agent find the entry points to this repo?

| Sub-component | Weight | What it measures |
|---|---:|---|
| `AGENTS.md` exists with required links | 30 | Top-level `AGENTS.md` linking to the codebase map, CLI manifest, and ADR directory. |
| Codebase map covers every module | 30 | Does `docs/codebase-map.md` mention every production module the adapter discovered? |
| CLI manifest fresh and complete | 20 | Does `docs/cli-manifest.json` exist, have at least N commands, and was touched in the last 7 days? |
| Root directory cleanliness | 20 | Are there stale artifacts (`.json`, `.bak`, `-results.*`) outside the allow-list? |

## Component 2 — Error quality (22%)

**Question:** How actionable are the repo's exceptions?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Fix-hint coverage | 50 | Percentage of throw/raise sites whose message contains the configured fix-hint marker. |
| User-defined exception ratio | 30 | Percentage of throws that use a domain exception class (not a stdlib generic). |
| Generic exception dominance | 20 | Do stdlib generics (`Exception`, `RuntimeError`, etc.) stay under 20% of throw sites? |

## Component 3 — Decision queryability (18%)

**Question:** How easily can an agent discover *why* the code is the way it is?

| Sub-component | Weight | What it measures |
|---|---:|---|
| ADR catalog | 60 | Does the configured ADR directory contain at least N files with valid frontmatter (`id:` key)? |
| Inline reference resolution | 40 | Percentage of inline decision tokens (e.g. `ADR-123`) in production source that resolve to an ADR body or filename. |

## Component 4 — Test quality (13%)

**Question:** Can an agent read a test name and know what it asserts?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Naming convention | 40 | Percentage of test methods matching the language's idiomatic naming pattern. |
| Helper file count | 30 | Does the repo have reusable test-helper files, not copy-paste fixtures? |
| Fixture duplication | 30 | Do configured duplication patterns stay rare? (Empty by default.) |

## Component 5 — Module hygiene (13%)

**Question:** Is the production tree organized neatly?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Internal visibility | 30 | Ratio of production files with at least one non-public type. |
| God files | 30 | Number of production files exceeding the configured LOC ceiling. |
| Doc-comment coverage | 20 | Percentage of public declarations with a doc comment. |
| Architecture doc freshness | 20 | Does the architecture doc exist and has it been touched recently? |

## Component 6 — Bootstrap signals (12%)

**Question:** Can a new contributor (or agent) install and run tests without
reading the full docs?

| Sub-component | Weight | What it measures |
|---|---:|---|
| CI-Signal | 50 | Does the repo define a runnable CI workflow? +30 pts for any workflow file, +20 pts when a workflow triggers on `pull_request`. |
| README-quality | 50 | Does the README's first 100 lines contain both an install command and a test command in fenced code blocks? |

Both are configurable via `[bootstrap_signals]` in `.agentrepocoach.toml`.

## Why these weights?

The 22/22/18/13/13/12 split is **heuristic, not empirically derived**. It
reflects a preference for the two components that pay off first on
almost any real repo:

- **Navigability** and **error quality** (44% of the score combined)
  are what an agent hits first in every single session. Bad `AGENTS.md`
  and opaque errors waste context on the most frequent path.
- **Decision queryability** (18%) starts to matter once the agent is
  past the "where am I?" phase and is asking "why?".
- **Test quality** and **module hygiene** (13% each) are tiebreakers —
  they compound over time but don't gate short sessions.
- **Bootstrap signals** (12%) is the floor — a repo that can't be
  installed or has no CI is hostile regardless of the other scores.

If you disagree, tune the weights in `.agentrepocoach.toml`. They must still
sum to 1.0 — AgentRepoCoach refuses to run otherwise.

## Reading a report

```json
{
  "schema_version": 2,
  "generator": "agentrepocoach 0.4.0",
  "total": 82.47,
  "components": {
    "navigability": { "score": 88.40, "weighted": 19.45, "sub_components": [...] },
    "error_quality": { "score": 82.20, "weighted": 18.08, "sub_components": [...] },
    "decision_queryability": { "score": 79.10, "weighted": 14.24, "sub_components": [...] },
    "test_quality": { "score": 80.67, "weighted": 10.49, "sub_components": [...] },
    "module_hygiene": { "score": 79.33, "weighted": 10.31, "sub_components": [...] },
    "bootstrap_signals": { "score": 83.33, "weighted": 10.00, "sub_components": [...] }
  }
}
```

Every `sub_components` entry carries the same transparency: the raw
count or percentage, the maximum, and the contribution to the component
score.

See [Methodology on GitHub](https://github.com/WouterDeBot/agentrepocoach/blob/main/docs/METHODOLOGY.md)
for the full spec including the language adapter contract.

---

AgentRepoCoach is licensed under **Apache 2.0**.
