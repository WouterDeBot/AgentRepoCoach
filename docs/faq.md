---
layout: page
title: FAQ
permalink: /faq/
---

# FAQ

### Why not use SonarQube, Codecov, or CodeClimate?

Because they measure something different. SonarQube and Codecov measure
**code health for humans** — cyclomatic complexity, duplication, test
coverage, security hotspots. Those are useful metrics but they don't
predict how well an AI agent will work in your repo.

AgentRepoCoach measures **agent-readiness**: can an autonomous coding agent
navigate the repo, understand the errors it hits, find the decisions
behind the code, and trust the tests? Those questions are orthogonal to
line coverage. A repo can have 95% test coverage and still be agent-hostile
if every exception is `throw new Exception("oops")` and every decision
lives in private Slack.

### Can I run it alongside Codecov / SonarQube?

Yes. AgentRepoCoach is a static scanner with zero runtime dependencies, so it
composes cleanly with any other CI tool. Many teams will want both: a
human-facing quality gate and an agent-facing readiness score.

### Which languages are supported?

| Language | Status | Notes |
|---|---|---|
| C# | Full MVP | Throw-site scanner, XML doc detection, internal visibility, .sln/.csproj discovery |
| Python | Full MVP | Raise-site scanner, docstring detection, top-level visibility, `src/` layout |
| TypeScript | Full MVP | Throw-site scanner with multi-line context, JSDoc detection, Jest/Vitest test extraction |
| Rust | Full MVP | `panic!`/`Err(Custom)` mapping, `///` doc comment detection, `#[test]` attribute detection |
| Go | Full MVP | `errors.New`/`fmt.Errorf`/custom error mapping, Go doc comment detection, `Test*` function extraction |

### How do I add a language?

Every language is one concrete `LanguageAdapter` subclass with nine
methods. Copy `src/agentrepocoach/adapters/typescript.py` to a new file,
implement the nine methods from `src/agentrepocoach/adapters/base.py`, and
register the class in `src/agentrepocoach/adapters/__init__.py::_REGISTRY`.

Full walkthrough in the root
[CONTRIBUTING.md](https://github.com/WouterDeBot/agentrepocoach/blob/main/CONTRIBUTING.md#adding-a-new-language-adapter).

### Why does the score refuse to run when weights don't sum to 1.0?

Because any drift would silently invalidate cross-repo comparisons.
AgentRepoCoach is a direction metric, so reproducibility matters — if your
score goes up by 2 points, you want to know that's because the repo
improved, not because the config drifted.

### Is AgentRepoCoach a CI gate?

It **can** be — set `fail-threshold: '70'` in the Action and the
workflow will exit 1 when the composite score drops below 70. But the
recommended use is **direction, not gate**: track the score over time,
let it drop occasionally on WIP branches, and use it to identify which
component pays off most this quarter.

### Why no runtime dependencies?

AgentRepoCoach scans repos in every conceivable CI environment, and adding
dependencies would slow installs and introduce supply-chain risk. The
Python 3.11+ standard library (including `tomllib`) has everything the
tool needs.

### Is AgentRepoCoach safe to run on proprietary code?

Yes. AgentRepoCoach never sends data anywhere and never emits code snippets
or raw error messages in its reports. Every field is a count, a
percentage, a type name, or a file path — so reports are safe to
publish as CI artifacts, even on closed-source codebases.

### Does AgentRepoCoach use AI to score the repo?

No. AgentRepoCoach is a static scanner written in pure Python. It does not
call any model, online or offline. The *target* of the metric is "how
well will an AI agent work in this repo," but the measurement itself is
100% deterministic static analysis.

### What's the best subreddit / forum to ask questions?

GitHub Discussions on the
[AgentRepoCoach repo](https://github.com/WouterDeBot/agentrepocoach/discussions) —
it keeps conversations indexed with the code.

---

AgentRepoCoach is licensed under **Apache 2.0**.
