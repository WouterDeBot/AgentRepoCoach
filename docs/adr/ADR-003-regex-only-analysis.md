---
id: ADR-003
status: accepted
date: 2025-01-20
---

# ADR-003: Regex-only analysis (no AST parsing)

## Context

Language adapters need to find declarations, raise/throw sites, and test
methods in source files. Two approaches were considered:

1. **AST parsing** -- accurate but requires language-specific parser libraries
   (tree-sitter, Roslyn, etc.), violating ADR-001 (zero dependencies).
2. **Regex scanning** -- less accurate on edge cases but works with stdlib
   only and is fast enough for repo-level scans.

## Decision

All language adapters will use **regex-only analysis**. No AST parsing
libraries will be imported. Each adapter defines its own compiled regex
patterns for declarations, throw sites, and test methods.

## Consequences

- Some edge cases (multi-line signatures, nested classes, decorators) may be
  missed or misclassified. This is acceptable because the CAH score is a
  heuristic, not a compiler.
- Adding a new language adapter is straightforward: define ~5 regex patterns,
  no parser setup required.
- If a language's syntax makes regex impractical (e.g., Haskell), that
  language may need a different approach or may not be supportable.
