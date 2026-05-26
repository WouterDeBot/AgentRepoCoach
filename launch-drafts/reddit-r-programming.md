# Reddit launch draft — AgentRepoCoach

## Subreddit pick

**Primary recommendation: r/ClaudeAI or r/LocalLLaMA.**

r/programming is usually hostile to Show-HN-style posts and tends to
auto-flag GitHub launches as self-promotion. r/ClaudeAI and
r/LocalLLaMA both have a large contingent of people who actually run
coding agents against their own repos and would understand the
"agent-readiness" framing immediately. r/github is a reasonable
backup; r/opensource works for the methodology angle.

**Do NOT post to r/programming** without extensive rewriting — and
even then expect downvotes. The karma won't be worth it.

## Title (300 chars max)

AgentRepoCoach: a 0-100 score for how ready your codebase is for AI coding agents (Apache 2.0, stdlib Python, GitHub Action)

## Body

I built a small open-source tool that answers one question: **how well
will an AI coding agent actually work in this repo?**

Not "does it have good test coverage" — that's a different question and
Codecov already handles it well. AgentRepoCoach measures the stuff that
actually burns context on every agent session: is there an `AGENTS.md`,
are your exception messages actionable, do your inline `ADR-123`-style
references resolve anywhere, are your test names readable, are your
modules small enough to hold in a context window, and does your CI
actually run and your README have real content?

It's built on 6 components: **navigability, error quality, decision
queryability, test quality, module hygiene, and bootstrap_signals**
(CI-Signal + README-quality, added in v0.4.0). Weighted 22/22/18/13/13/12
into a 0-100 composite called CAH.

Runs as a GitHub Action or a CLI. Zero runtime dependencies (pure
Python 3.11+ stdlib, including `tomllib` for config). Every field in
the output is a count, a percentage, or a file path — never a code
snippet — so it's safe to publish reports on closed-source repos too.

All five adapters (C#, Python, TypeScript, Go, Rust) are full MVP since
v0.2.0 — each includes throw-site scanners, doc detectors, test
extractors, and synthetic fixtures. Contributions for additional
languages welcome.

The weights are heuristic (I couldn't find a labelled dataset of
"agent success" to fit against), so the most useful feedback is
**cases where the score is wrong** — repos that score low but are
actually great, or the reverse.

Apache 2.0, v0.4.0. Feedback very welcome.

Repo: <REPO_URL>
