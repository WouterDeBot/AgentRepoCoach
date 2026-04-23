---
id: ADR-005
status: accepted
date: 2025-02-10
---

# ADR-005: Language adapter abstraction pattern

## Context

The CAH score must work across multiple programming languages (C#, Python,
TypeScript, Rust, Go). Each language has different conventions for file layout,
exception handling, test naming, and visibility modifiers.

Two patterns were considered:

1. **Strategy pattern with an abstract base class** -- one adapter class per
   language, all implementing the same 9-method interface. Components call
   adapter methods without knowing the language.
2. **Configuration-driven approach** -- a single generic scanner parameterized
   by config (file extensions, regex patterns, directory conventions). No
   subclasses.

## Decision

Use the **strategy pattern** with `LanguageAdapter` as the abstract base class
in `adapters/base.py`. Each language gets its own module file
(e.g., `adapters/python.py`) with a concrete subclass.

## Consequences

- Adding a new language means creating one file with ~150 lines of regex
  patterns and method implementations. No component code changes needed.
- The adapter interface has 9 methods; all must be implemented even if some
  return empty results for a given language.
- Auto-detection works by calling `detect()` on every registered adapter and
  picking the highest confidence score.
- The registry in `adapters/__init__.py` must be updated when adding a new
  adapter.
