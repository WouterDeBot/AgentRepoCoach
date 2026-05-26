# GitHub Marketplace Listing — AgentRepoCoach

This file is the source-of-truth text to copy-paste into the GitHub
Marketplace listing form when submitting AgentRepoCoach as a public Action.
The form fields below map 1:1 to the Marketplace UI.

## Listing fields

### Short description (≤ 125 chars, headline)

> Score your codebase on how ready it is for AI agents — and coach you through the fixes.

(116 chars)

### Primary category

`Code Quality`

### Secondary category

`Continuous Integration`

### Icon

`check-circle` (already wired in `action.yml branding.icon`)

### Color

`green` (already wired in `action.yml branding.color`)

### Long description

AgentRepoCoach computes the **Codebase Agent Health (CAH)** score: a single
0-100 composite measuring how friendly a repository is for autonomous
AI agents (Claude Code, Cursor, Aider, Continue, OpenHands, and the
rest of the wave).

It blends six statically-measurable components:

- **Navigability (22%)** — `AGENTS.md` presence, codebase map, CLI manifest, root cleanliness
- **Error quality (22%)** — fix-hint coverage, exception typing, generic-exception dominance
- **Decision queryability (18%)** — ADR catalog, inline reference resolution
- **Test quality (13%)** — naming convention, helper presence, fixture duplication
- **Module hygiene (13%)** — internal visibility, god files, doc coverage, architecture doc freshness
- **Bootstrap signals (12%)** — CI workflow on PR triggers, install + test commands in README

### Why it exists

Most code-quality tools are written for human reviewers. AgentRepoCoach is
written for the agents reading the codebase first. It scores the
properties that determine whether an autonomous coding agent can
navigate, modify, and verify your repo without burning context on
plumbing — and shows you exactly which files to fix first.

### Features

- Zero runtime dependencies (Python 3.11+ stdlib only)
- Full support for 5 languages: C#, Python, TypeScript, Go, and Rust (schema v2, 6 components)
- Coaching recommendations — top-3 actionable fix tips ranked by weighted impact
- TOML config (`.agentrepocoach.toml`) with sensible zero-config defaults
- JSON and Markdown output formats
- `fail-threshold` input for PR gating (CI fails if score drops below your bar)
- Composite GitHub Action (no Docker pull, no slow cold start)
- Apache 2.0 licensed
- All output is counts, paths, and identifiers — never source snippets, so reports are safe to publish as CI artifacts

### Quick-start (copy into a workflow)

```yaml
name: codebase-health

on:
  push:
    branches: [main]
  pull_request:

jobs:
  agentrepocoach:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run AgentRepoCoach
        id: agentrepocoach
        uses: WouterDeBot/agentrepocoach@v1
        with:
          repo-path: .
          output-format: json
          output-path: ./agentrepocoach-report.json
          fail-threshold: '70'

      - name: Show composite score
        run: echo "Score: ${{ steps.agentrepocoach.outputs.composite-score }}"

      - uses: actions/upload-artifact@v4
        with:
          name: agentrepocoach-report
          path: ./agentrepocoach-report.json
```

### Screenshot

`SCREENSHOT_URL_PLACEHOLDER`

(Suggested screenshot: terminal output of `python -m agentrepocoach.cli --repo .
--verbose` showing the per-component breakdown table on a real OSS
repository, plus a small inset of the JSON report.)

### Tags

`code-quality`, `ai-agents`, `static-analysis`, `developer-tools`,
`codebase-health`, `score`, `cli`, `github-action`

### Pricing

Free (Apache 2.0 OSS).

### Support links

- Issues: https://github.com/WouterDeBot/agentrepocoach/issues
- Discussions: https://github.com/WouterDeBot/agentrepocoach/discussions
- Docs: https://WouterDeBot.github.io/agentrepocoach

### Submission notes

- The action is **composite** (not Docker / not Node), so review
  should be fast.
- No `secrets` are read by the action. No outbound network calls
  beyond `pip install` of the action's own package on the runner.
- All inputs default to safe values; the action runs out-of-the-box
  with `uses: WouterDeBot/agentrepocoach@v1` and zero `with:` keys.
