# AgentRepoCoach: Score Your Codebase on AI Agent Readiness

*Draft v0.1 — for personal blog / dev.to. ~1,000 words.*

---

If you have ever watched an AI coding agent get dropped into a real
repository for the first time, you already know the first ten minutes
look roughly the same everywhere. The agent runs `ls`. Then `ls -R`.
Then it tries to read the README, fails to find a `CONTRIBUTING.md`,
hunts around for a test runner, greps for "TODO", opens three random
files, and finally — maybe five thousand tokens in — starts doing
something useful.

The surprising part is how little of this has to do with the agent.
Put a smart human into the same repo and they would be lost for a
similar amount of time. The difference is that the human has a career's
worth of pattern-matching to fall back on, and the agent has whatever
fits in its context window. *Every single session.*

That got me thinking: what would a repository look like if it were
optimized, deliberately, for AI agents to work in? Not retrofitted with
clever prompts, but actually structured so that a fresh agent could
be productive in two minutes instead of twenty?

After a lot of trial and error on a fairly large codebase, I ended up
with five things that seemed to matter more than anything else:

1. **A top-level `AGENTS.md`** that points at the three or four files
   an agent must read to orient itself.
2. **Exception messages that tell you how to fix the problem**, not
   just that something went wrong.
3. **Decision records you can grep for.** If the code references
   `ADR-014`, there had better be an `ADR-014` file somewhere.
4. **Tests you can read.** Test names that describe behaviour, helpers
   that reduce copy-paste, fixtures that don't bloat every file.
5. **Modules small enough to hold in your head.** No 2,000-line
   god files that burn a whole context window on a single scan.

Those five things became the five components of a metric I started
calling **CAH** — Codebase Agent Health. Each component is scored 0-100
and weighted into a single 0-100 composite. The weights are heuristic
(more on that below), but the sub-components are all things a static
scanner can measure in under a second.

Once the metric worked on one repo, the obvious next step was to turn
it into a tool that anyone can run on their own code. That's
[**AgentRepoCoach**](<REPO_URL>).

## What AgentRepoCoach does

AgentRepoCoach is a Python CLI and a GitHub Action. You point it at a repo
and it produces a single 0-100 score plus a breakdown by component:

```
AgentRepoCoach report — repo at .
==============================
Total score:        82.47 / 100
  navigability         22.10 / 25.00
  error_quality        20.55 / 25.00
  decision_queryability 15.82 / 20.00
  test_quality         12.10 / 15.00
  module_hygiene       11.90 / 15.00
```

Every field in the report is a count, a percentage, or a file path —
never a code snippet — so the JSON report is safe to publish as a CI
artifact even on proprietary code. There is no model call, no external
service, no network I/O of any kind. It's pure stdlib Python; `pip
install agentrepocoach` adds zero runtime dependencies.

## How to use it

As a GitHub Action:

```yaml
- uses: WouterDeBot/agentrepocoach@v1
  with:
    repo-path: .
    fail-threshold: '70'
```

As a CLI:

```bash
pip install agentrepocoach
python -m agentrepocoach.cli --repo . --verbose
```

The `--verbose` flag expands every component into its sub-components so
you can see exactly which field is pulling the score down. In my
experience, the first run on an existing codebase is always slightly
embarrassing and very instructive.

## How it works

AgentRepoCoach auto-detects the primary language of your repo (C# and
Python are fully supported in v0.1.0; TypeScript, Rust, and Go are
stubs waiting for contributors), loads a language adapter, and runs
five component scorers against the adapter's view of the code. Every
component is a handful of simple, transparent checks — no machine
learning, no magic, no hidden weights. You can read all the source on
GitHub in about an hour.

## About those weights

The 25/25/20/15/15 split is heuristic. I did not fit weights against
a labelled dataset of "agent success" because no such dataset exists
yet. Instead, the weights encode two design judgments: first, that the
two components an agent hits first in every session (navigation and
error messages) should dominate the score; second, that test quality
and module hygiene are tiebreakers that compound over time but rarely
decide individual sessions.

If you have a better weighting — or a dataset that would let us fit
weights empirically — please open an issue. I would rather rewrite the
defaults based on evidence than watch everyone silently tune their way
to 90.

## Roadmap

v0.1.0 is intentionally scoped small:

- [x] C# and Python adapters (full MVP)
- [x] GitHub Action + CLI
- [x] TOML config with per-field overrides
- [x] JSON + markdown output
- [ ] TypeScript adapter (stub; contributions welcome)
- [ ] Rust adapter (stub; contributions welcome)
- [ ] Go adapter (stub; contributions welcome)
- [ ] Multi-language monorepo scoring
- [ ] A published case-study dataset so we can tune weights empirically

## Call for contributors

AgentRepoCoach is Apache 2.0. The thing I would most love help with is a
language adapter — each one is ~200-400 lines of Python and opens the
tool up to a whole new ecosystem. After that, I would love people to
run it against popular OSS repos and write up the before/after.

If you try it, the single most valuable feedback you can give me is
**where the score is wrong**: a repo that scores low but is actually
great, or a repo that scores high but is actually terrible. Either
means my heuristics need work, and I want to know.

Apache 2.0. This is v0.1.0 — it is going to have rough edges. Feedback
very welcome.

Repo: <REPO_URL>
