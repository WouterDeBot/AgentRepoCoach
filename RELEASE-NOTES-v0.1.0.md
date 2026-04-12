# v0.1.0 — Initial Release

AgentRepoCoach scores your codebase on how ready it is for AI agents — and coaches you through the fixes.

## What it does

Scores a repository across 5 components (weights in parens):

- **Navigability** (25%) — `AGENTS.md`, codebase map, CLI manifest, root cleanliness
- **Error Quality** (25%) — exception subclassing, hint coverage, generic-exception dominance
- **Decision Queryability** (20%) — inline decision refs, ADR catalog presence
- **Test Quality** (15%) — helper file reuse, fixture dedup, naming convention
- **Module Hygiene** (15%) — internal visibility, god files, architecture doc freshness

## Usage

### As a GitHub Action

```yaml
- uses: WouterDeBot/agentrepocoach@v0.1.0
  with:
    repo-path: .
```

### As a CLI

```bash
pip install agentrepocoach
python -m agentrepocoach.cli --repo .
```

## What's supported

- C# (full)
- Python (full)
- TypeScript, Rust, Go (stubs — contribute!)

## Highlights

- Zero runtime dependencies (Python 3.11+ stdlib only, including `tomllib`)
- Composite Action (no Docker, no slow cold start)
- TOML config (`.agentrepocoach.toml`) with zero-config defaults
- JSON + Markdown output formats
- `fail-threshold` input for PR gating
- Output is safe to publish as a CI artifact (no source snippets)

## Feedback

This is v0.1.0. Feedback welcome via [GitHub Issues](https://github.com/WouterDeBot/agentrepocoach/issues)
and [Discussions](https://github.com/WouterDeBot/agentrepocoach/discussions).

## License

Apache 2.0
