# CAH Methodology — How AgentRepoCoach Scores a Repository

AgentRepoCoach computes the **Codebase Agent Health (CAH)** score: a single
0-100 composite measuring how structurally ready a repository is for autonomous
AI coding agents. The score is based entirely on static analysis — no code
execution, no network calls, no LLM inference. It measures inputs to agent
performance (structure, documentation signals, error explainability), not
outcomes. A repo that scores 90 can still have bugs; a repo that scores 40
will routinely frustrate agents regardless of how capable those agents are.

---

## The composite formula

    CAH = 0.22 * navigability
        + 0.22 * error_quality
        + 0.18 * decision_queryability
        + 0.13 * test_quality
        + 0.13 * module_hygiene
        + 0.12 * bootstrap_signals

Source: `src/agentrepocoach/config.py:33-40` (default weights) and
`src/agentrepocoach/compute.py:51-53` (weighted summation loop).

Weights must sum to 1.0 (validated at config-load time,
`src/agentrepocoach/config.py:262-271`). They are configurable per repo via
`.agentrepocoach.toml` under `[weights]`, but changing them breaks cross-repo
comparability — the defaults exist to make apples-to-apples comparison
meaningful.

### Why these weights?

The 22/22/18/13/13/12 split encodes two heuristics, not empirical regression (no
labelled dataset of "agent session success vs repo properties" exists yet):

1. **Frequency of impact.** Navigability and error quality are the first two
   components an agent touches in every session — navigation before writing a
   single line, errors on every failing test or broken import. They dominate
   because they dominate in practice.
2. **Compounding vs. per-session.** Test quality and module hygiene compound
   across many sessions but rarely determine whether a single session succeeds
   or fails. 13% each reflects that: enough to matter in the composite, not
   enough to swamp the high-frequency components.

Decision queryability sits between them at 18%: it matters enormously when an
agent is about to make an architectural change, but not at all for a
routine bug fix. 18% is the average across task types.

Bootstrap signals at 12% was added in v0.4.0 as a structural prerequisite
signal: CI configuration and README quality measure the foundational baseline
a repo needs before agents can even run code. A repo that can't be installed
or has no CI workflow is hostile to agents regardless of how well the other
five components score.

---

## Components

### 1. Navigability (22 pts of CAH)

**What it measures.** Whether an agent arriving at an unfamiliar repository
can orient itself without running `ls -R` and `grep` for fifteen minutes.
Specifically: is there a dedicated `AGENTS.md` entry point? Does a codebase
map enumerate every production module? Is the CLI surface documented in a
machine-readable manifest? Is the root directory clean of stale artifacts?

**WHY for agents — failure mode addressed.** Agents are token-constrained.
When a repo has no `AGENTS.md` and no codebase map, an agent must infer the
module layout from file paths alone, which produces incomplete mental models.
In practice, agents working on repos without these documents spend 20-40% of
a session on orientation-class tool calls (repeated `list_files`, broad
`search_files` sweeps) before reaching the task. A stale CLI manifest is
similarly dangerous: an agent may confidently invoke a command that was
renamed three releases ago. The `AGENTS.md` specification
(https://agents.md) was designed precisely to address this failure class — it
is a dedicated, predictable location for the context agents need to start
working. Aider's repo-map (https://aider.chat/docs/repomap.html) addresses
the same gap from the agent-client side via tree-sitter symbol extraction and
graph-ranked file lists; AgentRepoCoach scores whether the repo itself
provides equivalent signal statically.

**Sub-components and weights** (source: `src/agentrepocoach/components/documentation.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| `AGENTS.md` exists with required links | 30 | File exists AND links to codebase map, CLI manifest, and ADR dir | L25, L62-93 |
| Codebase map mentions every production module | 30 | `docs/codebase-map.md` contains every module name from the language adapter | L26, L96-136 |
| CLI manifest fresh and complete | 20 | `docs/cli-manifest.json` exists, has >= N commands, touched within 7 days | L27, L139-175 |
| Root directory cleanliness | 20 | Root contains no stale artifacts (`.json`, `.bak`, `-results.*`) outside allow-list | L28, L178-205 |

**Calibration notes.** CLI manifest freshness threshold defaults to 7 days
fresh / 14 days stale (`config.py:79-81`). The ADR directory link check in
`AGENTS.md` is a string-presence test, not a file-existence check; the file
must contain the configured path string. Codebase-map module coverage is a
simple substring match against module names returned by the language adapter.

**Limitations.** The `AGENTS.md` check does not validate that the content is
useful — a file with one line scores the same as a well-structured agent
guide. The CLI manifest freshness check uses file mtime, which resets on any
touch regardless of content change. Repos that auto-generate the manifest in
CI will typically score full marks here.

---

### 2. Error quality (22 pts of CAH)

**What it measures.** How actionable are the exceptions and error messages
raised by production code? An agent reasoning about a failure needs to know
what went wrong, why, and how to recover — from the error message alone,
without reading the surrounding code.

**WHY for agents — failure mode addressed.** The single most common agent
failure in debugging tasks is a cryptic exception: `InvalidOperationException("bad state")`,
`raise Exception("oops")`, `panic!("unexpected")`. These give an agent nothing
to reason about. The agent must infer cause from stack traces and surrounding
code, which burns tokens and often produces wrong conclusions. Two structural
fixes are measurable statically: (a) whether the exception message includes an
actionable hint ("Suggested fix: ..."), and (b) whether the codebase uses a
typed exception hierarchy so an agent can distinguish `AuthenticationError`
from `NetworkTimeoutError` from `ValidationError` without reading the handler.
The third sub-component (generic-exception dominance) measures whether the
codebase has simply wired everything through `Exception` or `RuntimeError`,
which collapses the information content of every failure to zero.

**Sub-components and weights** (source: `src/agentrepocoach/components/error_quality.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| Fix-hint coverage | 50 | % of throw/raise sites whose message contains the configured hint marker | L24, L84-105 |
| User-defined exception ratio | 30 | % of throws using a user-defined (domain) exception class vs stdlib generic | L25, L108-132 |
| Generic exception dominance | 20 | % of throw sites using language-stdlib generic types; lower is better | L26, L135-162 |

**Calibration notes.** Fix-hint full credit is awarded at 50% coverage
(`L27: _HINT_FULL_PCT = 50.0`) — not 100%, because many throw sites are
guard assertions where "Suggested fix" does not apply. The hint marker string
is configurable (`error_quality.hint_marker` in config; default: `"Suggested fix:"`).
Domain exception auto-discovery (`L59-81`) scans declaration names ending in
`Exception` or `Error`; explicit config list takes priority. Generic exception
dominance full credit is awarded below 20% generic; penalty starts above 40%
(`L29-30: _GENERIC_LOW_PCT`, `_GENERIC_HIGH_PCT`).

**Limitations.** Error quality is measured at throw sites, not catch sites.
A codebase that silently swallows exceptions (empty `except:` blocks) is not
penalised by this component. Hint-marker matching is a string search — a
message like "Suggested fix: delete everything" scores the same as a
genuinely useful hint. Exception type names are matched by declaration name,
not inheritance; a class named `MyError` that does not extend `Exception`
still counts as user-defined.

---

### 3. Decision queryability (18 pts of CAH)

**What it measures.** Whether an agent can discover *why* the code is the way
it is — not just what it does. Specifically: does the repository maintain an
ADR (Architecture Decision Record) catalog, and do inline references in
production code resolve to entries in that catalog?

**WHY for agents — failure mode addressed.** When an agent proposes an
architectural change, it needs to know whether the current approach is
accidental or intentional. Without an ADR catalog, the agent has no way to
distinguish "this was a deliberate tradeoff" from "nobody thought about it."
It will either make the change (breaking a load-bearing decision) or refuse
(introducing unnecessary friction). Inline references (`ADR-042` in a code
comment) compound this: they promise the reader that a decision is documented,
but a dangling reference is worse than no reference — the agent will search
for `ADR-042`, fail to find it, and lose trust in the entire comment layer.

**Sub-components and weights** (source: `src/agentrepocoach/components/decision_queryability.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| ADR catalog | 60 | Count of `.md` files in configured ADR dir with valid frontmatter (`id:` key) | L29, L47-79 |
| Inline reference resolution | 40 | % of unique inline ADR tokens in production source that resolve to an ADR body or filename | L30, L97-134 |

**Calibration notes.** ADR catalog full credit requires 20 valid ADRs
(`config.py:77: adr_min_count = 20`). Valid frontmatter requires a YAML
fence (`---`) with an `id:` key in the first 40 lines
(`decision_queryability.py:82-94`). Inline reference patterns default to
`ADR-\d+` and are configurable; patterns are word-boundary anchored to prevent
substring noise (`L137-152`). Resolution is a two-pass check: the token must
appear in either the body text or the filename of any ADR in the configured
directory (`L169-198`). Inline reference resolution full credit is awarded at
90% resolution (`L29: _REF_FULL_PCT = 90.0`).

**Limitations.** Frontmatter validity is checked by `id:` key presence only —
the tool does not validate that the ADR body is coherent or non-empty. A repo
with 20 one-line ADR stubs scores full marks on the catalog sub-score. The
inline reference regex matches token shape, not semantic meaning; a codebase
that comments `ADR-999` for a private tracking system (not public ADRs) will
produce false references.

---

### 4. Test quality (13 pts of CAH)

**What it measures.** Whether an agent can read a test name and know what it
asserts — without running the test or reading the test body. Also: whether the
test suite has enough shared helper infrastructure to make safe refactoring
feasible, and whether copy-paste fixture code has been brought under control.

**WHY for agents — failure mode addressed.** Agents that cannot understand
the test suite cannot safely refactor. If a test is named `test_case_7` or
`TestMethod3`, the agent has no signal about what behaviour it protects. The
agent must read the body, run the test, and infer — all of which costs tokens
and introduces risk. Worse, when every test starts with the same 30-line
fixture setup, an agent adding a new field must edit every test file. A test
suite with shared helpers and idiomatic names dramatically reduces the surface
area an agent must touch to make a safe change. Note that this component
measures *test readability and infrastructure*, not coverage — coverage is
handled by Codecov, Jest, and their friends.

**Sub-components and weights** (source: `src/agentrepocoach/components/test_quality.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| Naming convention | 40 | % of test methods matching the language adapter's idiomatic naming pattern | L27, L54-81 |
| Helper file count | 30 | Count of source files under the resolved helpers directory | L28, L84-112 |
| Fixture duplication | 30 | Configured duplication patterns appear rarely (full credit if patterns unset) | L29, L141-186 |

**Calibration notes.** Naming convention full credit is awarded at 100%
conformance (linear scale from 0% to 100%, `L74`). Helper file count full
credit is at 10 helper files (`config.py:106`; configurable via
`test_quality.helpers_full_count`). Helper directory auto-discovery checks
for `TestHelpers`, `test_helpers`, `helpers`, `fixtures`, `conftest` as
directory names under any test file's parent (`L115-138`). Fixture duplication
patterns are empty by default — the sub-score awards full credit unless the
operator opts in by listing project-specific patterns (`L147-151`).

**Limitations.** Naming convention matching is done via the language
adapter's `test_naming_pattern()` regex, which is language-idiomatic but
cannot enforce semantic naming (a method named `test_when_input_is_empty` is
structurally valid whether or not the body actually tests empty input). The
helper file count is a file count, not a quality score — a directory of
empty stub files counts the same as a well-maintained fixtures library.

---

### 5. Module hygiene (13 pts of CAH)

**What it measures.** Whether the production module tree is organized with
clear boundaries — internal types are marked internal, god files are rare,
public APIs are documented, and the architecture document has been touched
recently enough to reflect the current structure.

**WHY for agents — failure mode addressed.** Agents working in a poorly
organized module tree face two compound failures: (a) context explosion, where
a 2,000-line file forces the agent to load far more than it needs for any
single task, and (b) symbol ambiguity, where every declaration is public so
the agent cannot tell which symbols are safe to rename or delete without
breaking callers. An architecture document that is two years out of date is
worse than no architecture document — the agent builds a mental model from it
that contradicts the actual code. Internal visibility markers (`private`,
`internal`) are the language-native way to communicate module boundaries; when
they are absent, agents must infer boundaries from convention alone.

**Sub-components and weights** (source: `src/agentrepocoach/components/module_hygiene.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| Internal visibility | 30 | Ratio of production files that declare at least one non-public type | L23, L54-85 |
| God files | 30 | Count of production files exceeding the LOC ceiling (lower is better) | L24, L88-123 |
| Doc-comment coverage | 20 | % of public declarations with an attached doc comment | L25, L126-152 |
| Architecture doc freshness | 20 | Architecture doc exists and was modified within the configured window | L26, L155-175 |

**Calibration notes.** Internal visibility full credit is awarded at 10% of
production files containing at least one `internal`/`private` declaration
(`config.py:113: internal_visibility_full_ratio = 0.10`). God-file LOC
ceiling defaults to 800 lines (`config.py:75`); full penalty at 15 or more
god files, full credit at 5 or fewer (`module_hygiene.py:27-28`). Doc-comment
coverage full credit requires 90% of public declarations documented
(`config.py:77: doc_comment_min_coverage_pct = 90.0`). Architecture doc
freshness full credit within 60 days; half credit if the file exists but is
stale (`module_hygiene.py:155-175`).

**Limitations.** Internal visibility is detected by the language adapter's
`scan_declarations()` method, which classifies visibility from language
keywords — a Python function without a leading underscore is classified
`public` even if it is only used internally. God-file LOC counting uses raw
line count including blanks and comments, which slightly inflates counts for
heavily-commented files. Architecture doc freshness is based on file mtime,
not content quality.

---

### 6. Bootstrap signals (12 pts of CAH)

**What it measures.** Whether the repo has CI configured and whether the
README explains how to install and test the project. These are the two
prerequisites for any agent to bootstrap a working development environment.

**WHY for agents — failure mode addressed.** An agent that cannot run tests
cannot verify its changes. A CI signal tells the agent whether a PR-based
workflow exists and provides an automated correctness gate. The README quality
check (install + test commands in the first `readme_head_lines` lines, default
100) measures whether a fresh agent can get to a runnable state from the README
alone. Without these signals, agents must guess the build system, the test
runner, and the PR workflow — which leads to broken-environment failures that
have nothing to do with the agent's reasoning quality. Bootstrap signals were
added in v0.4.0 as the sixth component because they function as a structural
prerequisite: a repo scoring poorly here is hostile to agents regardless of
how well the other five components score.

**Sub-components and weights** (source: `src/agentrepocoach/components/bootstrap_signals.py`):

| Sub-component | Max pts | What it checks | Line ref |
|---|---:|---|---|
| `ci_signal` | 50 | Does the repo have a CI workflow that runs on PRs? 30 pts for any workflow file; +20 pts when a workflow triggers on `pull_request:` or `pull_request_target:`. | L20, L56-89 |
| `readme_quality` | 50 | Does the README contain a fenced install command AND a fenced test command within the first `readme_head_lines` lines (default 100)? 25 pts for install; 25 pts for test. | L21, L116-179 |

**Note on the max-points key.** Bootstrap signals sub-component dicts use
`"total"` as the max-points key (not `"max"` like all other components). Any
code reading sub-component dicts must use:
```python
maximum = sub.get("total", sub.get("max", 0))
```
This is documented in `CLAUDE.md` as a codebase gotcha.

**Calibration notes.** CI signal checks `.github/workflows/*.yml`,
`.github/workflows/*.yaml`, `.gitlab-ci.yml`, and `.circleci/config.yml` by
default (`config.py:154-159`). The PR-trigger detection covers three YAML
forms: scalar (`on: pull_request`), flow sequence (`on: [pull_request, push]`),
and block-map (`on:\n  pull_request:`). README quality scans only the first
`readme_head_lines` lines (default 100; configurable via
`[bootstrap_signals] readme_head_lines = N` in `.agentrepocoach.toml`) to
keep the signal honest: a README that buries install instructions on page 3
is not agent-friendly. Install and test command patterns are configurable via
`install_command_patterns` and `test_command_patterns` in `[bootstrap_signals]`.

**Limitations.** CI signal detection is a regex check on file content, not
a semantic analysis of the workflow. A workflow that is technically present
but always skipped, disabled, or gated behind a condition will still pass the
structural check. README quality checks for fenced code blocks only — prose
instructions (without backtick fences) do not count. The byte cap
(`_README_BYTE_CAP = 200_000`) skips README scoring on extremely large files
as a DoS guard.

**Private and single-operator repos.** The `readme_quality` sub-component
(50 pts of `bootstrap_signals`) rewards README content — install and test
fenced code blocks — that is primarily useful for a *first-time external user*
orienting themselves in a fresh clone. For a private repo used by a single
operator who already knows how to install and run the project, these blocks
are a one-time papercut fix (five README lines) that improves documentation
without meaningfully changing day-to-day agent session quality.

The fix is quick: adding `` ```bash pip install -e . ``` `` and
`` ```bash pytest tests/ ``` `` in the first 100 README lines earns the full
50 pts. If you prefer not to add documentation that isn't genuinely useful to
your workflow, you can lower the `bootstrap_signals` weight via `[weights]` or
set `repo_type = "private-internal"` in `.agentrepocoach.toml` to apply a
reduced default weight (0.06 instead of 0.12, with the 0.06 redistributed to
`navigability`). Be aware that this breaks cross-repo comparability with repos
that use the default weights — scores are only directly comparable when the
weight profiles match.

---

## Decision queryability — the differentiating angle

Most agent-readiness tools in the current landscape (Factory.ai, Kodus,
Kenogami-AI — see `fleet/handoffs/2026-05-24-lens-sota.md` §2d for the
competitive map) measure human-maintainability proxies: test presence, CI
configuration, dependency freshness. None name decision queryability as a
first-class metric. The lens-sota finding from 2026-05-24: "The crowded area
is: 'does this repo have tests, docs, and CI?' The emptier area is: decision
queryability (ADRs, inline reference resolution)... None of the three
competitors name these explicitly."

This gap is defensible because the failure mode it targets is qualitatively
different from "missing tests" or "bad docs." An agent that cannot find *why*
a decision was made will either repeat known-bad approaches (because it cannot
see the rejection rationale in an ADR) or block on a change that is actually
safe (because it cannot tell whether the constraint is intentional). An ADR
catalog gives the agent a queryable record of the repo's design history.
Inline reference resolution closes the loop: a comment that says `see ADR-042`
is worthless unless `ADR-042` actually exists and its body contains the
referenced decision. CAH measures both ends of the chain — catalog presence
and reference integrity — making the score a stronger proxy for "can an agent
understand design intent" than either signal alone.

---

## What CAH does NOT measure

- **Runtime test coverage** — line/branch/mutation coverage is handled by
  Codecov, Jest coverage reports, and similar. CAH measures test readability
  and infrastructure, not how much of the code is exercised.
- **Security vulnerabilities** — no SAST, no dependency CVE scan, no secrets
  detection. Use `bandit`, `semgrep`, `trivy`, or Dependabot alongside
  AgentRepoCoach for security posture.
- **Runtime correctness** — AgentRepoCoach never executes your code. A 95-
  scoring repo can still be riddled with bugs.
- **Performance characteristics** — no hot-path analysis, no big-O estimates,
  no profiling. A 500-line god file that runs in microseconds gets the same
  penalty as a 500-line function that runs in an hour.
- **Dependency freshness** — Dependabot does this well. CAH does not scan
  lock files or package registries.
- **Production code duplication** — only fixture duplication (in tests, opt-
  in) is flagged. Production-level duplication detection is better handled by
  `jscpd`, `simian`, or `pmd-cpd`.
- **LLM-graded coherence** — CAH is entirely static. It does not ask an LLM
  whether your documentation makes sense, whether your architecture is
  consistent, or whether your error messages are actually helpful. It only
  checks measurable structural signals.
- **Actual agent performance on tasks** — CAH is a plausible proxy for agent-
  readiness, not a benchmark. No labelled dataset of "repo properties vs.
  agent task success" exists yet. The score rewards things agents repeatedly
  complain about; it does not guarantee a correlation with success rates on
  any specific agent benchmark.
- **IDE or language-server integration quality** — hover documentation,
  go-to-definition, symbol renaming, and similar IDE features are not
  measured. CAH measures source-code structure, not tooling integration.
- **Team process signals** — PR review latency, commit frequency, code
  ownership — none of these are in scope. CAH is a snapshot of the
  repository's static structure, not a team health metric.

---

## How to read a score

The composite score is a direction signal, not a grade. A score of 72 does
not mean "72% of the way to being a good codebase" — it means "the weighted
mix of six structural properties currently sits at 72, and the components
below their expected ceiling are the highest-leverage places to improve agent-
friendliness."

**Reading the output.** The coaching engine (`src/agentrepocoach/output.py:194-228`)
ranks sub-component gaps by `gap * component_weight`, surfacing the fix with
the highest weighted impact first. Look at the top coaching tip before looking
at the overall score — a single tip often covers 10-15 points of composite
improvement.

**Example.** A Python repo scores:

```
navigability:           85 / 100   (weight 0.22  →  18.70 pts)
error_quality:          40 / 100   (weight 0.22  →   8.80 pts)
decision_queryability:  60 / 100   (weight 0.18  →  10.80 pts)
test_quality:           90 / 100   (weight 0.13  →  11.70 pts)
module_hygiene:         75 / 100   (weight 0.13  →   9.75 pts)
bootstrap_signals:      70 / 100   (weight 0.12  →   8.40 pts)
---
CAH total:              68 / 100
```

The coaching engine identifies `error_quality.hint_coverage` (gap: 60 pts,
weight-adjusted impact: 13.2 pts) as the top fix. Adding `"Suggested fix: ..."
suffixes to half of the existing raise sites would push `error_quality` from
40 to roughly 65, lifting the composite to around 75 — a 7-point gain from
one targeted change. The score does not tell you to rewrite anything; it
tells you where the next agent session is most likely to be frustrated.

---

## References and inspiration

1. **AGENTS.md spec** — https://agents.md — The community standard for
   AI agent configuration files; the `AGENTS.md` sub-score in Navigability
   directly measures conformance with this spec.

2. **Aider repo-map** — https://aider.chat/docs/repomap.html — Aider's
   tree-sitter + PageRank approach to building a ranked symbol map within a
   token budget; the Codebase Map sub-score in Navigability rewards the static
   equivalent: a human-maintained map that the agent can read without inference.

3. **Claude Code best practices (Anthropic)** —
   https://www.anthropic.com/engineering/claude-code-best-practices —
   Anthropic's guidance on `CLAUDE.md` structure and agent context design;
   informs the Navigability component's view of what "entry point documentation"
   should contain.

4. **Architecture Decision Records (ADRs) — Michael Nygard's original proposal** —
   https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions —
   The original ADR format (status / context / decision / consequences) that
   the Decision Queryability component's valid-frontmatter check (`id:` key)
   is designed to be compatible with.

5. **Factory.ai Agent Readiness** — https://factory.ai/agent-readiness —
   Commercial predecessor in the agent-readiness scoring space; CAH's
   differentiating angle is decision queryability and zero-dependency
   static scoring (no account required).

6. **Kodus agent-readiness** — https://github.com/kodustech/agent-readiness —
   Open-source competitor covering 7 pillars, 39 checks; does not score
   ADR catalog or inline reference resolution.

7. **Kenogami-AI codebase-readiness** — https://github.com/Kenogami-AI/codebase-readiness —
   LLM-hybrid approach to agent-readiness scoring; requires LLM inference at
   score time, not CI-friendly for offline or regulated environments.

8. **CLAUDE.md specification (Anthropic Claude Code docs)** —
   https://docs.anthropic.com/en/release-notes/claude-code —
   The Claude Code project's own agent configuration file format; the
   `AGENTS.md` check is designed to be compatible with Claude Code's
   `/init`-generated entry point documentation.

---

*This document is the canonical reference for the CAH scoring methodology.
Source code for each component is in `src/agentrepocoach/components/`.
Configuration reference is in `docs/configuration.md`. To propose a
change to weights or thresholds, open a GitHub Discussion with evidence —
the defaults are calibrated for cross-repo comparability.*
