# v0.2.0 — Full Language Coverage + Coaching Recommendations

AgentRepoCoach now scores repos in 5 languages and tells you exactly what to fix first.

## What's new

### Full language adapters for TypeScript, Go, and Rust

All three previously-stubbed adapters are now fully implemented:

- **TypeScript** — `tsconfig.json`/`package.json` detection, throw-site scanning with multi-line context, JSDoc detection, Jest/Vitest test method extraction
- **Go** — `go.mod` detection, `errors.New`/`fmt.Errorf`/custom error mapping, Go doc comment detection, `Test*` function extraction
- **Rust** — `Cargo.toml` detection, `panic!`/`Err(Custom)` mapping, `///` doc comment detection, `#[test]` attribute detection

All adapters use regex-only analysis (no AST parser dependencies) and implement the full 9-method `LanguageAdapter` interface.

### Coaching recommendations engine

AgentRepoCoach no longer just scores your repo — it coaches you through the fixes. The new coaching engine:

- Analyzes sub-component score gaps across all five components
- Surfaces the **top-3 actionable fix tips** ranked by weighted impact
- Works in every output format: terminal summary, verbose mode, markdown PR comments, and JSON reports (new `coaching` array)

### Dogfood improvements

AgentRepoCoach now scores 100/100 on its own repo:

- `AGENTS.md` for agent-friendly codebase navigation
- `codebase-map.md` for repo structure overview
- `cli-manifest.json` for CLI discoverability
- `docs/architecture.md` documenting the system design
- 5 Architecture Decision Records (ADRs)
- Fix hints on all raise sites; docstrings on all public declarations

## Bug fixes

- Python adapter `_TEST_METHOD_PATTERN` was missing `re.MULTILINE` flag, causing zero test methods to be detected in Python repositories

## What's supported

| Language   | Status   |
|------------|----------|
| C#         | Full MVP |
| Python     | Full MVP |
| TypeScript | Full MVP |
| Go         | Full MVP |
| Rust       | Full MVP |

## Highlights

- Still zero runtime dependencies (Python 3.11+ stdlib only, including `tomllib`)
- Composite Action (no Docker, no slow cold start)
- TOML config (`.agentrepocoach.toml`) with zero-config defaults
- JSON + Markdown output formats
- `fail-threshold` input for PR gating
- Output is safe to publish as a CI artifact (no source snippets)

## Upgrade

### GitHub Action

```yaml
- uses: WouterDeBot/agentrepocoach@v0.2.0
```

### CLI

```bash
pip install --upgrade agentrepocoach
```

## Feedback

Feedback welcome via [GitHub Issues](https://github.com/WouterDeBot/agentrepocoach/issues)
and [Discussions](https://github.com/WouterDeBot/agentrepocoach/discussions).

## License

Apache 2.0
