---
type: research-finding
status: complete
from: fe-research-agent
to: fleet-manager
created: 2026-06-08
topic: claude-md-best-practices
---

# Research: CLAUDE.md Best Practices for AgentRepoCoach

## Summary

Anthropic's official documentation establishes a clear standard for CLAUDE.md: keep it under 200 lines, make every instruction verifiable and non-obvious, and cut anything Claude could infer on its own. For AgentRepoCoach specifically, the highest-leverage content is the zero-dependency constraint (stated as a prohibition, not a description), the three ADRs that constrain every implementation decision, the language-adapter extension pattern, and explicit demarcation of `fleet/` as AI-managed state. The existing `AGENTS.md` is a strong foundation and should be imported by CLAUDE.md rather than duplicated.

## Key Findings by Question

### Q1: Official Anthropic Guidance

**The official include/exclude matrix** (source: [code.claude.com/docs/en/best-practices](https://code.claude.com/docs/en/best-practices)):

Include: Bash commands Claude can't guess, code style rules that differ from defaults, testing instructions and preferred test runners, repository etiquette, architectural decisions specific to the project, developer environment quirks, common gotchas or non-obvious behaviors.

Exclude: Anything Claude can figure out from reading code, standard language conventions Claude already knows, detailed API documentation (link instead), information that changes frequently, long explanations or tutorials, file-by-file codebase descriptions, self-evident practices like "write clean code."

**CLAUDE.md is context, not enforcement.** From the memory page: "Claude reads it and tries to follow it, but there's no guarantee of strict compliance." Hard enforcement requires hooks.

**AGENTS.md interop is explicitly documented.** The recommended pattern for repos that already have AGENTS.md: create a CLAUDE.md that starts with `@AGENTS.md` to import it. This applies directly to AgentRepoCoach.

### Q2: Highest-Impact Content

1. **Build/test commands** are the single highest-ROI content. Without them, Claude guesses.
2. **Hard architectural constraints** that override Claude's defaults. Claude defaults to reaching for third-party libraries, AST parsers, and helpful output snippets — all three of which are prohibited by ADR-001/002/003.
3. **Extension patterns** — the adapter recipe (where new things go, how to add them) is exactly the content official docs recommend.
4. **Non-obvious test gotchas** — `tests/fixtures/` are synthetic sample repos, not test files; `norecursedirs` in pyproject.toml prevents collection but Claude doesn't know why.

### Q3: Anti-Patterns

- **Style conventions already enforced by ruff** — pure token waste; the linter catches these deterministically.
- **File-by-file codebase descriptions** — explicitly in the official exclude column; `docs/codebase-map.md` exists for this.
- **Contradictory instructions** — importing AGENTS.md rather than duplicating it eliminates this risk.
- **Over-200-line files** — adherence degrades measurably; the official hard limit is 200 lines.
- **Self-evident practices** — "write clean code," "add comments," etc. are negative-value: they consume context with no behavioral benefit.

### Q4: Python CLI + PyPI + pytest + GitHub Actions + Multi-Language Adapter Specifics

- **Zero-dep constraint** must be a prohibition: "Do not add runtime dependencies. `dependencies = []` must remain empty." Current AGENTS.md states it descriptively; CLAUDE.md should state it as a rule with `IMPORTANT` emphasis.
- **PyPI**: version lives only in `pyproject.toml` `version` field — state this explicitly to prevent common drift mistakes.
- **pytest fixture isolation**: `tests/fixtures/` contains synthetic repos used as INPUT. Never add pytest functions inside it. The `norecursedirs` setting exists for this reason.
- **CI workflow names**: `ci.yml` (main tests), `cah-score.yml` (self-scoring), `dogfood.yml` (dogfood) — naming these prevents Claude from describing a generic pipeline.
- **Adapter pattern**: the 5-step recipe in AGENTS.md is the correct content; preserve it via the `@AGENTS.md` import.

### Q5: Length and Structure

- Official hard limit: **200 lines** per CLAUDE.md file.
- HumanLayer's own root file is **under 60 lines** — with heavy content in subdirectory files.
- **Use markdown headers and bullets**, not prose — Claude scans structure.
- **`IMPORTANT` / `YOU MUST` emphasis** improves adherence for critical rules — reserve it for the zero-dep constraint and the fleet/ rule.
- Pruning test: "Would removing this cause Claude to make a mistake?" If not, cut it.

### Q6: Fleet-Engine / AI-Managed State

No specific published guidance exists for fleet-engine projects. The general pattern (explicit prohibition with rationale) is well-established. Proposed content:

```
## AI-managed state (fleet/)
`fleet/` is managed exclusively by the Fleet Engine orchestration system.
Do NOT manually edit files under `fleet/state/`, `fleet/handoffs/`, or
`fleet/memory/`. Read them for context; never write to them directly.
```

## Recommendations (priority order)

1. **Import AGENTS.md as the foundation**: First line of CLAUDE.md should be `@AGENTS.md`. Add only Claude-specific content below. This keeps the file well under 200 lines by default.

2. **State zero-dep as an explicit prohibition with emphasis**: "**IMPORTANT: Do not add any runtime dependencies.** The `dependencies` list in `pyproject.toml` must remain empty. Stdlib only (Python 3.11+). This is ADR-001 — not a preference."

3. **Add fleet/ protection rule**: Document `fleet/` as AI-managed state that should never be manually written. Rationale prevents Claude from "cleaning up" perceived stale files.

4. **Add pytest fixture gotcha**: `tests/fixtures/` are synthetic repos used as INPUT, not test files. Never add pytest functions inside them.

5. **State ADRs as active constraints, not archive refs**: Name what each means operationally (no deps / no source in output / regex only).

6. **Omit all ruff-enforced style rules**: snake_case, line length, import ordering — all handled deterministically by the linter.

7. **Target under 100 lines of net-new content** (excluding the @AGENTS.md import): The import + zero-dep rule + fleet/ rule + fixture gotcha + ADR summary is achievable in ~50-60 lines.

## Open Questions

1. Does `claude -p` (non-interactive/CI mode) load CLAUDE.md from the repo? If so, should CI-specific instructions be gated?
2. Should `@docs/codebase-map.md` be imported (adding ~70 lines of context per session) or referenced as a pointer?
3. Should there be a `CLAUDE.local.md.example` committed to guide contributors with per-machine overrides?
4. Is there a fleet-engine convention for flagging which CLAUDE.md content was Fleet-Manager-approved vs. human-authored?

## Sources

- [Official best practices — Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [Store instructions and memories — Claude Code Docs](https://code.claude.com/docs/en/memory)
- [Writing a good CLAUDE.md — HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Claude Code anti-patterns — AI Codex](https://www.aicodex.to/articles/claude-code-antipatterns)
- [CLAUDE.md Best Practices for Beginners — Medium](https://medium.com/data-science-in-your-pocket/claude-md-best-practices-for-beginners-e57876bb04e2)
- [What Is the Claude.md File — MindStudio](https://www.mindstudio.ai/blog/what-is-claude-md-file-ai-agents)
- Project files: AGENTS.md, pyproject.toml, CONTRIBUTING.md, docs/codebase-map.md, docs/architecture.md

STATUS: complete
