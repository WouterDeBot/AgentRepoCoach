---
id: ADR-002
status: accepted
date: 2025-01-15
---

# ADR-002: No source code in output

## Context

AgentRepoCoach scores arbitrary repositories, some of which contain
proprietary code. If the JSON or Markdown output included raw code snippets,
error message bodies, or comment text, running the tool in CI could
inadvertently leak intellectual property into logs or PR comments.

## Decision

Output formats (JSON, Prometheus, Markdown) will contain **only** counts,
percentages, exception type names, and file paths. No raw source lines,
error message bodies, or comment text will appear in any output artifact.

## Consequences

- Components must aggregate findings into numeric scores, not echo source.
- Debugging a score requires re-running with `--verbose`, which prints
  sub-component metadata (counts, ratios) but still no source text.
- Future features like "show me the worst error message" would violate this
  ADR and must not be added without a new decision.
