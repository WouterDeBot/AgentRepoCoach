# HN Show HN draft — AgentRepoCoach

*Title (80 char max):*

Show HN: AgentRepoCoach – Score your codebase on AI agent readiness

*Body (2-4 short paragraphs, URL in the first line of text, no
salesy language — HN hates marketing tone):*

---

Repo: <REPO_URL>

I kept noticing that AI coding agents burn a large chunk of their
context window in the first few minutes of every session just figuring
out where to look in a new repo: no `AGENTS.md`, opaque exception
messages, decision references that don't resolve anywhere, 2,000-line
god files. After manually fixing one of my own repos to be more
agent-friendly, I pulled the heuristics out into a standalone tool.

AgentRepoCoach is a Python CLI and a composite GitHub Action that scores a
repository on six components — navigability, error quality, decision
queryability, test quality, module hygiene, and **bootstrap signals**
(CI-Signal + README-quality). `bootstrap_signals` is a v0.4.0 addition
covering whether your CI is wired and your README is substantive. The
tool produces a single 0-100 composite called Codebase Agent Health (CAH).
Every number in the report is a count, a percentage, or a file path —
no code snippets — so the JSON output is safe to publish as a CI
artifact on closed codebases too. Zero runtime dependencies
(stdlib-only, including `tomllib` for config parsing). All five adapters
(C#, Python, TypeScript, Go, Rust) are full MVP since v0.2.0;
contributions for additional languages welcome.

The 22/22/18/13/13/12 weighting (v0.4.0 rebalance after adding
`bootstrap_signals` as the 6th component) is heuristic — I did not fit
it against a labelled dataset of "agent success" because no such dataset
exists yet. The weight provenance is documented in `docs/METHODOLOGY.md`
in the repo. So the single most useful feedback I'm hoping for is cases
where the score is wrong: repos that score low but are actually great to
work in, or repos that score high but are actually terrible. Either means
my heuristics need work, and I want to know which way.

Apache 2.0, v0.4.1. Some rough edges expected. The repo has a GitHub
Action you can drop into any workflow in about 10 lines, and the CLI
installs with `pip install agentrepocoach`.
