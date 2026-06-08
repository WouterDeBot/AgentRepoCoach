"""Benchmark script for agentrepocoach — dev tool, not shipped in the package.

Generates synthetic Python repos of configurable sizes in a temp directory,
times ``agentrepocoach <tmpdir>`` for each size, and prints a summary table.

Usage:
    python scripts/benchmark.py

Requires only stdlib (no third-party deps). Python 3.11+.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Synthetic repo generation
# ---------------------------------------------------------------------------

_PYPROJECT_TOML = textwrap.dedent("""\
    [build-system]
    requires = ["setuptools>=69"]
    build-backend = "setuptools.backends.legacy:build"

    [project]
    name = "mypackage"
    version = "0.1.0"
    requires-python = ">=3.11"
    dependencies = []
""")

_README_MD = textwrap.dedent("""\
    # mypackage

    ## Overview

    A synthetic package generated for benchmarking AgentRepoCoach.

    ## Installation

    ```bash
    pip install -e .
    ```

    ## Usage

    ```bash
    python -m mypackage
    ```
""")

_ARCHITECTURE_MD = textwrap.dedent("""\
    # Architecture

    ## Decision: Use a flat package layout

    This package uses a flat `src/` layout for clarity.

    ## Decision: Stdlib only

    No runtime dependencies are introduced.
""")


def _module_source(index: int) -> str:
    """Return source for a synthetic Python module."""
    return textwrap.dedent(f"""\
        \"\"\"Module {index:04d} — synthetic module for benchmarking.\"\"\"
        from __future__ import annotations


        class Widget{index:04d}:
            \"\"\"A widget class for module {index:04d}.\"\"\"

            def compute(self, value: int) -> int:
                \"\"\"Compute a result from value.

                Suggested fix: pass a positive integer.
                \"\"\"
                if value < 0:
                    raise ValueError(
                        f"value must be non-negative, got {{value}}. "
                        "Suggested fix: pass a positive integer."
                    )
                return value * {index}

            def describe(self) -> str:
                \"\"\"Return a human-readable description.\"\"\"
                return f"Widget{index:04d}(index={index})"
    """)


def _test_source(index: int) -> str:
    """Return source for a synthetic test file."""
    return textwrap.dedent(f"""\
        \"\"\"Tests for module {index:04d}.\"\"\"
        from mypackage.module_{index:04d} import Widget{index:04d}


        def test_compute_positive_widget_{index:04d}() -> None:
            widget = Widget{index:04d}()
            assert widget.compute(2) == 2 * {index}


        def test_describe_widget_{index:04d}() -> None:
            widget = Widget{index:04d}()
            assert "Widget{index:04d}" in widget.describe()
    """)


def generate_repo(tmpdir: Path, n_files: int) -> None:
    """Generate a synthetic Python repo with approximately n_files total files.

    Distribution: ~70% src .py, ~20% test .py, ~10% other (toml, md, docs).
    """
    # Fixed overhead files (count as part of the ~10% "other")
    (tmpdir / "pyproject.toml").write_text(_PYPROJECT_TOML)
    (tmpdir / "README.md").write_text(_README_MD)

    docs_dir = tmpdir / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text(_ARCHITECTURE_MD)

    src_dir = tmpdir / "src" / "mypackage"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text(
        '"""mypackage — synthetic package."""\n__all__: list[str] = []\n'
    )

    tests_dir = tmpdir / "tests"
    tests_dir.mkdir()

    # Calculate module and test counts from target n_files.
    # Fixed overhead: pyproject.toml, README.md, docs/architecture.md,
    # src/mypackage/__init__.py = 4 files.
    remaining = max(n_files - 4, 1)
    n_modules = max(int(remaining * 0.78), 1)   # ~70% of total
    n_tests = max(int(remaining * 0.22), 1)     # ~20% of total

    for i in range(1, n_modules + 1):
        (src_dir / f"module_{i:04d}.py").write_text(_module_source(i))

    for i in range(1, n_tests + 1):
        (tests_dir / f"test_{i:04d}.py").write_text(_test_source(i))


def count_files(repo: Path) -> int:
    """Count all files in a repo tree."""
    return sum(1 for _ in repo.rglob("*") if _.is_file())


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_score(repo: Path) -> tuple[float, float]:
    """Run agentrepocoach against repo and return (wall_time_s, score).

    The CLI is invoked as a subprocess so timing includes the full startup
    cost (import, detection, scoring) — representative of CI usage.
    """
    cmd = [sys.executable, "-m", "agentrepocoach.cli", "--repo", str(repo), "--quiet"]

    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0

    score: float = 0.0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.replace(".", "", 1).isdigit():
            try:
                score = float(stripped)
            except ValueError:
                pass
            break

    return elapsed, score


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

SIZES = [100, 1000, 5000]


def main() -> None:
    print("AgentRepoCoach benchmark — generating synthetic Python repos …\n")

    rows: list[tuple[int, int, float, float]] = []

    for target_size in SIZES:
        with tempfile.TemporaryDirectory(prefix="arc_bench_") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            generate_repo(tmpdir, target_size)
            actual_count = count_files(tmpdir)

            print(f"  Scoring {actual_count:,} files (target {target_size:,}) … ", end="", flush=True)
            elapsed, score = run_score(tmpdir)
            print(f"{elapsed:.2f}s  score={score:.1f}")

            rows.append((target_size, actual_count, elapsed, score))

    # Print summary table
    print()
    print(f"{'Files (target)':>15}  {'Files (actual)':>15}  {'Wall time (s)':>13}  {'Score':>6}")
    print("-" * 58)
    for target, actual, wall, score in rows:
        print(f"{target:>15,}  {actual:>15,}  {wall:>12.2f}s  {score:>6.1f}")

    print()
    print("Note: scores on synthetic repos are low by design — they lack AGENTS.md,")
    print("ADR catalogs, CLI manifests, and other structural signals that real repos have.")


if __name__ == "__main__":
    main()
