@AGENTS.md

---

## Critical rules

**IMPORTANT: Do not add runtime dependencies.** `dependencies = []` in `pyproject.toml` must stay empty. Stdlib only (Python 3.11+). ADR-001 is a hard supply-chain constraint, not a style preference. Do not reach for third-party libraries even for test utilities.

**IMPORTANT: Do not write to `fleet/`.** `fleet/state/`, `fleet/handoffs/`, and `fleet/memory/` are managed by the Fleet Engine orchestration system. Read them for context; never write to them directly.

---

## Architecture gotchas

**Filename ≠ component name:** `components/documentation.py` implements the **`navigability`** component. Do not rename it to match.

**Dual max-key convention in sub-component dicts:** `bootstrap_signals` uses `"total"` as the max-points key; all other components use `"max"`. Any code reading sub-component dicts must use:
```python
maximum = sub.get("total", sub.get("max", 0))
```

**`--all-languages` silently ignores flags:** `--compare`, `--prometheus`, `--comment`, `--verbose`, `--format markdown|both` are no-ops in `--all-languages` mode. This is a known limitation (IMP-004) — do not attempt to wire these without a design pass.

**`Config` is a frozen dataclass.** Direct attribute assignment raises `FrozenInstanceError`. Use `dataclasses.replace(config, field=value)`.

---

## Tests and fixtures

`tests/fixtures/` contains **synthetic sample repos used as scoring INPUT** — they are not test code. Never add pytest functions inside them. `norecursedirs` in `pyproject.toml` prevents accidental pytest collection.

`conftest.py` calls `_touch_recent_files()` at session start to refresh mtime on fixture files (`docs/cli-manifest.json`, `docs/architecture.md`). Without this, freshness-based sub-scores return 0 on cold clones. If you bypass the pytest session, call it manually.

---

## Version and release

VERSION lives in exactly **two files** — both must be bumped in the same commit:
1. `pyproject.toml` — `version = "X.Y.Z"` (line 7)
2. `src/agentrepocoach/__init__.py` — `VERSION = "X.Y.Z"`

Release order: version-bump commit → `python -m build` → `twine upload` → annotated tag → `git push --tags` → `gh release create`. The tag **must be on the version-bump commit**, and `pyproject.toml` version must match the tag name before any PyPI upload.

---

## Scoring model (schema_version = 2)

```
CAH = 0.22 × navigability  +  0.22 × error_quality  +  0.18 × decision_queryability
    + 0.13 × test_quality  +  0.13 × module_hygiene  +  0.12 × bootstrap_signals
```

Weights must sum to 1.0 ± 0.01 or `ConfigError`. All six components must be present when customising `[weights]` in `.agentrepocoach.toml`. Scores are heuristic — see `docs/scoring.md`.
