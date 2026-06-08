
<!-- capture-hash:04373c08f12b8c93916f0b63b293019d14cdeaa1ea0aab0d0d7089edbcdd5ba5 -->
### SL-001 | project | 2026-06-08
**From:** auto-capture
**Validated:** pending
**Summary:** CLAUDE.md is context not enforcement; 200-line hard limit; import @AGENTS.md rather than duplicate; state zero-dep as prohibition not description

CLAUDE.md is context not enforcement; 200-line hard limit; import @AGENTS.md rather than duplicate; state zero-dep as prohibition not description

---

<!-- capture-hash:249a19a5fb124d4b13511f05c2d705888b596c0e08aa30c6258b70e6d72a916a -->
### SL-002 | codebase | 2026-06-08
**From:** auto-capture
**Validated:** pending
**Summary:** bootstrap_signals sub-components use "total" as the max-points key while all other components use "max" — use sub.get("total", sub.get("max", 0)) everywhere

bootstrap_signals sub-components use "total" as the max-points key while all other components use "max" — use sub.get("total", sub.get("max", 0)) everywhere

---

<!-- capture-hash:842a77d7bfb9f6902cf0b19ae6d9ee6207480f6e5840570347eabab89285191d -->
### SL-003 | tool-usage | 2026-06-08
**From:** auto-capture
**Validated:** pending
**Summary:** Write tool refuses to write files containing git conflict markers — use `git checkout --theirs <file> && git add` to resolve conflicts before editing

Write tool refuses to write files containing git conflict markers — use `git checkout --theirs <file> && git add` to resolve conflicts before editing

---

<!-- capture-hash:2e1c8fb149ef49e44c7a333c823c8cfb606c79b937eae75aa1a93261a148db26 -->
### SL-004 | methodology | 2026-06-08
**From:** auto-capture
**Validated:** pending
**Summary:** Process-level advisory guards (module-level bool flags) must be reset at the start of each test that asserts the advisory fires — same pattern as _warned_schemas.discard(N)

Process-level advisory guards (module-level bool flags) must be reset at the start of each test that asserts the advisory fires — same pattern as _warned_schemas.discard(N)

---
