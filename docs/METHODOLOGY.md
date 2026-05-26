# AgentRepoCoach Methodology

This document defines the **Codebase Agent Health (CAH)** score: a single
0-100 composite measuring how friendly a repository is for autonomous AI
agents. It also records the design decisions behind the metric so that
contributors can argue with the methodology, not just the code.

## Why these 6 components?

Most "code quality" metrics were designed for humans. They count lines,
track duplication, and flag security hotspots — all useful, but all
orthogonal to the question AgentRepoCoach asks: *how well will an AI coding
agent actually work in this repo?*

When you watch an agent session closely, almost every failure falls into
one of five buckets:

1. **The agent got lost.** No `AGENTS.md`, no codebase map, no CLI
   manifest — so the first fifteen minutes go to `ls -R` and `grep`.
2. **The agent hit an opaque error.** `throw new Exception("oops")` gives
   nothing to reason about, so the agent either guesses or gives up.
3. **The agent couldn't find the "why".** Decisions live in private Slack
   or year-old PRs; the code is a fact with no explanation.
4. **The agent couldn't trust the tests.** Test names are cryptic, helpers
   are missing, every fixture is copy-paste — so the agent can't safely
   refactor.
5. **The agent drowned in god files.** A 2,000-line file burns the whole
   context window; structure would have saved 90% of the tokens.

A sixth concern cuts across all of these: **can the repo even be set up?**
An agent (or human) that can't install and run tests is stuck before writing
a single line. The `bootstrap_signals` component captures this.

Each of the six CAH components targets exactly one of these failure
modes. That is why there are six, not three and not twelve: we wanted
enough coverage to reflect real sessions, and few enough that every
component has a clear behavioural story.

## The composite formula

    CAH = 0.22 * navigability
        + 0.22 * error_quality
        + 0.18 * decision_queryability
        + 0.13 * test_quality
        + 0.13 * module_hygiene
        + 0.12 * bootstrap_signals

Every component is computed by walking the working tree — no network,
no database, no language runtime invocations. The score is informational;
it is a **direction signal**, not a CI gate (though you *can* use it as
one via `fail-threshold`).

## How weights were chosen

The 22/22/18/13/13/12 split is **heuristic, not empirically derived**. We
did not run a multi-repo regression to fit weights against some
downstream "agent success" label because no such labelled dataset
exists yet (and we suspect building one would take a year).

Instead, the weights encode two design judgments:

1. **The two components an agent hits first should dominate.** In every
   session, the agent will navigate (Navigability) and hit errors
   (Error quality) long before it ever needs to read an ADR or audit a
   test suite. Frontload the weight on the components with the most
   frequent impact.
2. **Test quality and module hygiene are tiebreakers.** They compound
   over many sessions but rarely determine whether a single session
   succeeds. 13% each reflects that — enough to matter, not enough to
   swamp.
3. **Bootstrap signals (12%) is the floor.** A repo that can't be
   installed or has no CI workflow is hostile to agents regardless of
   how well the other five components score.

We explicitly recommend against "tuning your weights until your repo
scores well." The weights exist so that **cross-repo comparisons** are
meaningful; changing them per repo breaks that.

If you disagree with the defaults, open a discussion — we would rather
rewrite the defaults based on evidence than watch everyone silently
tune their way to 90.

## Components

### 1. Navigability (22 pts)

How easily does an agent find the entry points to the repo?

| Sub-component | Weight | What it measures |
|---|---:|---|
| `AGENTS.md` exists with required links | 30 | Does the repo have a top-level `AGENTS.md` that links to the codebase map, CLI manifest, and ADR directory? |
| Codebase map mentions every production module | 30 | Does `docs/codebase-map.md` reference every module the language adapter discovered? |
| CLI manifest is fresh and complete | 20 | Does `docs/cli-manifest.json` exist, have at least N commands, and has been touched in the last 7 days? |
| Root directory cleanliness | 20 | Are there stale artifacts (`.json`, `.bak`, `-results.*`) outside the configured allow-list? |

### 2. Error quality (22 pts)

How actionable are the repo's exceptions?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Fix-hint coverage | 50 | What percentage of throw/raise sites have a message containing an actionable fix hint (configurable marker)? |
| User-defined exception ratio | 30 | What percentage of throws use a user-defined (domain) exception class rather than a stdlib generic? |
| Generic exception dominance | 20 | Do language-stdlib generic exceptions (`Exception`, `RuntimeError`, etc.) stay under 20% of throw sites? |

### 3. Decision queryability (18 pts)

How easily can an agent discover **why** the code is the way it is?

| Sub-component | Weight | What it measures |
|---|---:|---|
| ADR catalog | 60 | Does the configured ADR directory contain at least N files with valid frontmatter (`id:` key)? |
| Inline reference resolution | 40 | What percentage of inline decision tokens (e.g. `ADR-123`) in production source resolve to an ADR body or filename? |

### 4. Test quality (13 pts)

Can an agent read a test name and know what it asserts?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Naming convention | 40 | What percentage of test methods match the language's idiomatic naming pattern? |
| Helper file count | 30 | Does the repo have enough reusable test-helper files to discourage copy-paste fixtures? |
| Fixture duplication | 30 | Do configured fixture-duplication patterns stay rare? (Empty by default — full credit unless opted in.) |

### 5. Module hygiene (13 pts)

Is the production tree organized neatly?

| Sub-component | Weight | What it measures |
|---|---:|---|
| Internal visibility | 30 | What ratio of production files declare at least one non-public type? (Visibility hygiene.) |
| God files | 30 | How many production files exceed the configured LOC ceiling? (Lower is better.) |
| Doc-comment coverage | 20 | What percentage of public declarations have a doc comment attached? |
| Architecture doc freshness | 20 | Does the configured architecture doc exist and has it been touched in the last 60 days? |

### 6. Bootstrap signals (12 pts)

Can a new contributor (or agent) install and run tests in the repo without
reading the full docs?

| Sub-component | Weight | What it measures |
|---|---:|---|
| CI-Signal | 50 | Does the repo define a runnable CI workflow (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`)? +30 pts for any workflow file, +20 pts when a workflow triggers on `pull_request`. |
| README-quality | 50 | Does the README's first 100 lines contain both an install command (`pip install`, `npm install`, `cargo`, `go install`, etc.) and a test command (`pytest`, `npm test`, `go test`, etc.) in fenced code blocks? |

Both sub-components are configurable via `[bootstrap_signals]` in
`.agentrepocoach.toml`. See the configuration reference for glob overrides
and pattern lists.

## Limitations

AgentRepoCoach is narrow on purpose. It is worth being explicit about what
the tool does **not** measure:

- **Runtime correctness.** AgentRepoCoach never executes your code. A repo
  that scores 95 can still be riddled with bugs — the tool measures
  the static surface, not the dynamic behaviour.
- **Security.** No SAST, no dependency CVE scan, no secrets detection.
  Use `bandit`, `semgrep`, `trivy`, or your favourite security scanner
  alongside AgentRepoCoach.
- **Performance.** AgentRepoCoach has no notion of hot paths, big-O, or
  profiling. A 500-line function that runs in microseconds gets the
  same god-file penalty as a 500-line function that runs in an hour.
- **Test coverage.** Coverage-by-line is handled beautifully by
  Codecov and friends; AgentRepoCoach only measures the *shape* of tests
  (naming, helpers, duplication), not how much of the code they hit.
- **Dependency freshness.** Dependabot does this well; we don't
  duplicate it.
- **Code duplication.** `jscpd`, `simian`, `pmd-cpd`, and others do
  this well; AgentRepoCoach only flags *fixture* duplication, not
  production duplication.
- **Actual agent performance.** CAH is a plausible proxy for
  agent-readiness, but it is not a labelled benchmark. Until someone
  publishes a multi-repo agent-success dataset, we cannot claim the
  score predicts agent success — only that it rewards the things
  agents repeatedly complain about.

If you want a full code-health picture, run AgentRepoCoach **alongside** the
tools above, not instead of them.

## Anti-patterns to avoid

These are the patterns that damage the CAH score and — more importantly —
damage the agent-development experience.

1. **Unactionable error messages.** "Invalid operation" gives an agent
   nothing to work with. Always include: what was expected, what was
   observed, and how to recover.
2. **Magic module layout.** Dozens of production modules with no file
   that lists them in one place forces grep-hunts every session.
3. **Undocumented public APIs.** A public class without a doc comment
   is a black box; the agent must read every call site.
4. **God files.** A 2,000-line file blows up the context window and
   makes every scan slower and noisier.
5. **Undifferentiated exception hierarchies.** If every failure is a
   `RuntimeError`, the agent cannot distinguish "bad input" from
   "database is down" without reading the string.
6. **Stale architecture docs.** A doc last touched a year ago may
   describe a codebase that no longer exists.
7. **Private inline refs without an index.** `FOO-123` in a comment is
   worthless if nothing in the repo resolves the token.
8. **Copy-paste fixture builders.** When every test starts with the
   same 25-line setup, adding a field means changing every test.
9. **Flat visibility.** When every declaration is public, every change
   is a potential breaking change; agents cannot tell which symbols
   are safe to modify.

## Language adapter contract

Every language adds one concrete `LanguageAdapter` subclass with nine
methods. The abstract contract lives in `src/agentrepocoach/adapters/base.py`.

- `detect(repo_path)` — return a 0.0-1.0 confidence score.
- `find_production_files(repo_path)` — return production source files.
- `find_test_files(repo_path)` — return test source files.
- `find_production_modules(repo_path)` — return logical module names.
- `scan_throw_sites(files, hint_marker, domain_exception_types)` — return
  `ThrowSite` descriptors.
- `generic_exception_names()` — return the stdlib types considered "too generic".
- `scan_declarations(files)` — return `Declaration` descriptors with
  visibility and doc-comment flag.
- `find_test_methods(files)` — return (file, method_name) tuples.
- `test_naming_pattern()` — return the regex for the idiomatic
  test-method name.

To add a new language, copy `src/agentrepocoach/adapters/typescript.py` (the
stub), implement the nine methods, and register the class in
`src/agentrepocoach/adapters/__init__.py::_REGISTRY`.

## Configuration

All thresholds, weights, paths, and patterns are configurable via
`.agentrepocoach.toml` at the repo root. The tool ships with sensible
defaults — the config file is opt-in tuning. Config files must declare
`schema_version = 2` (introduced in v0.4.0 alongside the 6th component).
See [`docs/configuration.md`](configuration.md) for the full schema
and the v1→v2 migration recipe.
