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

Those five things became the original five components of a metric I
started calling **CAH** — Codebase Agent Health; in v0.4.0 a sixth
(`bootstrap_signals`) was added covering CI/README presence. Each
component is scored 0-100 and weighted into a single 0-100 composite.
The weights are heuristic (more on that below), but the sub-components
are all things a static scanner can measure in under a second.

Once the metric worked on one repo, the obvious next step was to turn
it into a tool that anyone can run on their own code. That's
[**AgentRepoCoach**](<REPO_URL>).

## What AgentRepoCoach does

AgentRepoCoach is a Python CLI and a GitHub Action. You point it at a repo
and it produces a single 0-100 score plus a breakdown by component.
Here is the actual v0.4.0 dogfood result on the AgentRepoCoach repo itself:

```
AgentRepoCoach — Codebase Agent Health
=================================
Total score:   95.32 / 100
Language:      python

Components:
  navigability              100.00 / 100   weight=0.22   contribution= 22.00
  error_quality              80.00 / 100   weight=0.22   contribution= 17.60
  decision_queryability     100.00 / 100   weight=0.18   contribution= 18.00
  test_quality               97.82 / 100   weight=0.13   contribution= 12.72
  module_hygiene            100.00 / 100   weight=0.13   contribution= 13.00
  bootstrap_signals         100.00 / 100   weight=0.12   contribution= 12.00
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

AgentRepoCoach auto-detects the primary language of your repo, loads a
language adapter, and runs six component scorers against the adapter's
view of the code. All five adapters (C#, Python, TypeScript, Go, Rust)
are full MVP since v0.2.0 — each includes throw-site scanners, doc
detectors, test extractors, and synthetic fixtures. Every component is a
handful of simple, transparent checks — no machine learning, no magic,
no hidden weights. You can read all the source on GitHub in about an hour.

## About those weights

The 22/22/18/13/13/12 split is heuristic (rebalanced in v0.4.0 after
adding `bootstrap_signals` as the 6th component). I did not fit weights
against a labelled dataset of "agent success" because no such dataset
exists yet. Instead, the weights encode two design judgments: first,
that the two components an agent hits first in every session (navigation
and error messages) should dominate the score; second, that test quality
and module hygiene are tiebreakers that compound over time but rarely
decide individual sessions. The full weight provenance and methodology
are documented in `docs/METHODOLOGY.md`.

If you have a better weighting — or a dataset that would let us fit
weights empirically — please open an issue. I would rather rewrite the
defaults based on evidence than watch everyone silently tune their way
to 90.

## Roadmap

v0.4.1 is a more mature state but still pre-1.0 (v0.x). The rough
edges are real but the tool is dogfooded against its own repo (95.32/100)
and has 169 tests:

- [x] C#, Python, TypeScript, Go, Rust adapters (all full MVP since v0.2.0)
- [x] GitHub Action + CLI
- [x] TOML config with per-field overrides
- [x] JSON + markdown output
- [x] bootstrap_signals component (CI-Signal + README-quality, added v0.4.0)
- [ ] Multi-language monorepo scoring
- [ ] A published case-study dataset so we can tune weights empirically

## Call for contributors

AgentRepoCoach is Apache 2.0. The thing I would most love help with after
language adapters is running the tool against popular OSS repos and
writing up the before/after. A published dataset of scores would let us
tune the weights empirically instead of relying on my heuristics.

If you try it, the single most valuable feedback you can give me is
**where the score is wrong**: a repo that scores low but is actually
great, or a repo that scores high but is actually terrible. Either
means my heuristics need work, and I want to know.

Apache 2.0. This is v0.4.0 — feedback very welcome.

Repo: <REPO_URL>
