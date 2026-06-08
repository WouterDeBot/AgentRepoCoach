"""Implementation of the ``agentrepocoach history`` subcommand.

Shows CAH score trends across recent commits. Critically, this command
NEVER modifies the git working tree — it uses read-only ``git show HASH:filepath``
to extract file contents per commit into a temporary directory.

Zero runtime dependencies: stdlib only (Python 3.11+).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_COUNT = 20
_DEFAULT_COUNT = 5


@dataclass
class CommitEntry:
    """Scored result for a single commit."""
    short_hash: str
    date: str
    message: str
    score: float | None


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the CompletedProcess result."""
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _check_git_repo(cwd: Path) -> bool:
    """Return True if cwd is inside a git repository."""
    result = _run_git(["rev-parse", "--git-dir"], cwd)
    return result.returncode == 0


def _get_commits(cwd: Path, count: int) -> list[tuple[str, str, str]]:
    """Return a list of (full_hash, subject, date_iso) tuples.

    Returns an empty list if the repo has no commits or git fails.
    """
    result = _run_git(
        ["log", "--format=%H|%s|%ai", f"-{count}", "HEAD"],
        cwd,
    )
    if result.returncode != 0:
        return []

    entries: list[tuple[str, str, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        full_hash, subject, date_str = parts[0], parts[1], parts[2]
        # Normalise to YYYY-MM-DD only.
        date_short = date_str[:10] if date_str else ""
        entries.append((full_hash, subject, date_short))
    return entries


def _get_file_list(cwd: Path, commit_hash: str) -> list[str]:
    """Return the list of file paths present at *commit_hash*."""
    result = _run_git(["ls-tree", "-r", "--name-only", commit_hash], cwd)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _extract_commit_to_tempdir(cwd: Path, commit_hash: str, tmp: Path) -> None:
    """Populate *tmp* with the file contents of *commit_hash*.

    Uses ``git show HASH:filepath`` for each file — never touches the
    working tree.  Files that cannot be shown (e.g. binary, too large)
    are silently skipped.
    """
    file_list = _get_file_list(cwd, commit_hash)
    for rel_path in file_list:
        dest = tmp / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        result = _run_git(["show", f"{commit_hash}:{rel_path}"], cwd)
        if result.returncode != 0:
            # File may not exist at this commit or is binary — skip gracefully.
            continue
        try:
            dest.write_text(result.stdout, encoding="utf-8", errors="replace")
        except OSError:
            continue


def _score_tempdir(tmp: Path) -> float | None:
    """Compute the CAH score for the contents of *tmp*.

    Returns None when no language adapter can be auto-detected.
    """
    from .adapters import NoAdapterError
    from .compute import compute_cah
    from .config import load_config

    try:
        config = load_config(tmp)
        result = compute_cah(tmp, config=config)
        return float(result["total"])
    except (NoAdapterError, Exception):  # noqa: BLE001
        return None


def _score_commit(cwd: Path, commit_hash: str) -> float | None:
    """Extract a commit into a temp dir, score it, and clean up."""
    with tempfile.TemporaryDirectory(prefix="arc_history_") as tmp_str:
        tmp = Path(tmp_str)
        _extract_commit_to_tempdir(cwd, commit_hash, tmp)
        return _score_tempdir(tmp)


def _format_table(entries: list[CommitEntry]) -> str:
    """Render entries as a fixed-width text table."""
    header = f"{'HASH':<9}{'DATE':<12}{'SCORE':>6}  MESSAGE"
    separator = "-" * (9 + 12 + 8 + 2 + 40)
    rows = [header, separator]
    for e in entries:
        score_str = f"{e.score:>6.1f}" if e.score is not None else "   N/A"
        # Truncate long messages so the table stays readable.
        msg = e.message[:60] if len(e.message) > 60 else e.message
        rows.append(f"{e.short_hash:<9}{e.date:<12}{score_str}  {msg}")
    return "\n".join(rows)


def _format_json(entries: list[CommitEntry]) -> str:
    """Render entries as a JSON array."""
    records: list[dict[str, Any]] = []
    for e in entries:
        records.append({
            "hash": e.short_hash,
            "date": e.date,
            "score": e.score,
            "message": e.message,
        })
    return json.dumps(records, indent=2)


def run_history(args: Any) -> int:
    """Execute the ``history`` subcommand.

    Returns an exit code (0 = success, 1 = error).
    """
    count: int = getattr(args, "count", _DEFAULT_COUNT)
    fmt: str = getattr(args, "format", "table")
    cwd = Path.cwd()

    # Cap count at the maximum.
    if count > _MAX_COUNT:
        print(
            f"warning: --count {count} exceeds maximum ({_MAX_COUNT}); capping at {_MAX_COUNT}.",
            file=sys.stderr,
        )
        count = _MAX_COUNT

    # Validate we are inside a git repository.
    if not _check_git_repo(cwd):
        print(
            "error: not a git repository (or any of the parent directories). "
            "Run agentrepocoach history inside a git repo.",
            file=sys.stderr,
        )
        return 1

    commits = _get_commits(cwd, count)
    if not commits:
        print(
            "error: no commits found in this repository.",
            file=sys.stderr,
        )
        return 1

    results: list[CommitEntry] = []
    for full_hash, message, date in commits:
        short_hash = full_hash[:7]
        score = _score_commit(cwd, full_hash)
        results.append(CommitEntry(
            short_hash=short_hash,
            date=date,
            message=message,
            score=score,
        ))

    if fmt == "json":
        print(_format_json(results))
    else:
        print(_format_table(results))

    return 0
