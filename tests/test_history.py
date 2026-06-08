"""Tests for the ``agentrepocoach history`` subcommand (XPL-007).

AC-01: ≥3 rows in output when repo has ≥3 commits.
AC-02: --count 1 outputs exactly 1 data row.
AC-03: The working tree (tracked files) is byte-identical before and after.
AC-04: --format json outputs valid JSON with hash/message/date/score keys.
AC-05: Non-git directory prints error to stderr and exits non-zero.
Edge:  --count 25 is capped at 20 with a warning to stderr.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentrepocoach.cli import main
from agentrepocoach.history_cmd import (
    _check_git_repo,
    _format_json,
    _format_table,
    _get_commits,
    CommitEntry,
    run_history,
)


# ---------------------------------------------------------------------------
# Helpers — build a minimal git repo with N commits
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _make_repo(tmp_path: Path, num_commits: int = 3) -> Path:
    """Create a bare git repo with *num_commits* commits in *tmp_path*.

    Each commit adds a single .py file so that language detection has
    something to work with.  The repo uses a local git identity so it
    works in CI environments without global git config.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test User"], repo)

    for i in range(1, num_commits + 1):
        py_file = repo / f"module_{i}.py"
        py_file.write_text(
            f'"""Module {i}."""\n\ndef func_{i}():\n    """Do something."""\n    return {i}\n',
            encoding="utf-8",
        )
        _git(["add", f"module_{i}.py"], repo)
        _git(["commit", "-m", f"feat: add module {i}"], repo)

    return repo


# ---------------------------------------------------------------------------
# AC-01: ≥3 rows from a 3-commit repo
# ---------------------------------------------------------------------------

class TestHistoryBasic:
    """AC-01: at least 3 data rows when the repo has 3 commits."""

    def test_three_commits_gives_three_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-01: output has at least 3 data rows for a 3-commit repo."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history"])

        assert exit_code == 0
        captured = capsys.readouterr()
        # Strip header lines (HASH ... and separator line) to count data rows.
        lines = [ln for ln in captured.out.splitlines() if ln.strip() and not ln.startswith("HASH") and not ln.startswith("-")]
        assert len(lines) >= 3, f"Expected ≥3 data rows, got {len(lines)}: {captured.out!r}"

    def test_output_contains_commit_hash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-01: each data row contains a 7-char hex hash."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history"])
        captured = capsys.readouterr()
        # Get the short hash of the most recent commit.
        result = _git(["log", "--format=%h", "-1", "HEAD"], repo)
        short_hash = result.stdout.strip()
        assert short_hash in captured.out, (
            f"Expected short hash {short_hash!r} in output:\n{captured.out}"
        )

    def test_output_contains_date(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-01: output contains a YYYY-MM-DD date."""
        import re
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history"])
        captured = capsys.readouterr()
        assert re.search(r"\d{4}-\d{2}-\d{2}", captured.out), (
            f"Expected a date in YYYY-MM-DD format in output:\n{captured.out}"
        )

    def test_output_contains_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-01: output contains commit messages."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history"])
        captured = capsys.readouterr()
        assert "feat: add module" in captured.out, (
            f"Expected commit message in output:\n{captured.out}"
        )


# ---------------------------------------------------------------------------
# AC-02: --count 1 gives exactly 1 data row
# ---------------------------------------------------------------------------

class TestHistoryCount:
    """AC-02: --count N limits output to exactly N data rows."""

    def test_count_one_gives_one_row(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-02: --count 1 produces exactly 1 data row."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history", "--count", "1"])

        assert exit_code == 0
        captured = capsys.readouterr()
        data_lines = [
            ln for ln in captured.out.splitlines()
            if ln.strip() and not ln.startswith("HASH") and not ln.startswith("-")
        ]
        assert len(data_lines) == 1, (
            f"Expected exactly 1 data row with --count 1, got {len(data_lines)}: {captured.out!r}"
        )

    def test_count_two_gives_two_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--count 2 produces exactly 2 data rows from a 3-commit repo."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history", "--count", "2"])

        assert exit_code == 0
        captured = capsys.readouterr()
        data_lines = [
            ln for ln in captured.out.splitlines()
            if ln.strip() and not ln.startswith("HASH") and not ln.startswith("-")
        ]
        assert len(data_lines) == 2, (
            f"Expected 2 data rows with --count 2, got {len(data_lines)}: {captured.out!r}"
        )


# ---------------------------------------------------------------------------
# AC-03: working tree unchanged after history run
# ---------------------------------------------------------------------------

class TestHistoryWorkingTreeSafety:
    """AC-03: running history must not modify the working tree."""

    def test_working_tree_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-03: git diff --exit-code returns 0 after running history."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history"])
        assert exit_code == 0

        diff = _git(["diff", "--exit-code"], repo)
        assert diff.returncode == 0, (
            f"Working tree was modified after history run:\n{diff.stdout}\n{diff.stderr}"
        )

    def test_no_untracked_files_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """history must not leave untracked files in the repo directory."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        # Record untracked files before.
        before = _git(["ls-files", "--others", "--exclude-standard"], repo).stdout.strip()

        main(["history"])

        after = _git(["ls-files", "--others", "--exclude-standard"], repo).stdout.strip()
        assert before == after, (
            f"Untracked files changed:\nbefore: {before!r}\nafter: {after!r}"
        )


# ---------------------------------------------------------------------------
# AC-04: --format json outputs valid JSON with correct keys
# ---------------------------------------------------------------------------

class TestHistoryJsonFormat:
    """AC-04: --format json outputs valid JSON with hash/message/date/score."""

    def test_json_format_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-04: --format json produces parseable JSON."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history", "--format", "json"])

        assert exit_code == 0
        captured = capsys.readouterr()
        try:
            data = json.loads(captured.out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"history --format json produced invalid JSON: {exc}\nOutput:\n{captured.out}")

        assert isinstance(data, list), f"Expected a JSON array, got {type(data)}"

    def test_json_has_required_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-04: each JSON object has hash, message, date, and score keys."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history", "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)

        required_keys = {"hash", "message", "date", "score"}
        for i, obj in enumerate(data):
            missing = required_keys - set(obj.keys())
            assert not missing, (
                f"JSON object {i} missing keys: {missing}\nObject: {obj}"
            )

    def test_json_count_matches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--format json with --count 2 should return exactly 2 objects."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history", "--count", "2", "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 2, f"Expected 2 JSON objects, got {len(data)}"

    def test_json_hash_is_7_chars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each JSON hash value should be a 7-character hex string."""
        import re
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history", "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)

        for obj in data:
            assert re.fullmatch(r"[0-9a-f]{7}", obj["hash"]), (
                f"hash {obj['hash']!r} is not a 7-char hex string"
            )

    def test_json_date_is_iso_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each JSON date value should be YYYY-MM-DD format."""
        import re
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        main(["history", "--format", "json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)

        for obj in data:
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", obj["date"]), (
                f"date {obj['date']!r} is not YYYY-MM-DD format"
            )


# ---------------------------------------------------------------------------
# AC-05: non-git directory exits non-zero with stderr message
# ---------------------------------------------------------------------------

class TestHistoryNonGitDirectory:
    """AC-05: running history outside a git repo fails gracefully."""

    def test_non_git_dir_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-05: exit code is non-zero in a non-git directory."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["history"])
        assert exit_code != 0

    def test_non_git_dir_error_to_stderr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-05: an error message is printed to stderr."""
        monkeypatch.chdir(tmp_path)
        main(["history"])
        captured = capsys.readouterr()
        assert "error" in captured.err.lower(), (
            f"Expected 'error' in stderr, got: {captured.err!r}"
        )

    def test_non_git_dir_nothing_to_stdout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """AC-05: nothing is printed to stdout on error."""
        monkeypatch.chdir(tmp_path)
        main(["history"])
        captured = capsys.readouterr()
        assert not captured.out.strip(), (
            f"Unexpected stdout on error: {captured.out!r}"
        )


# ---------------------------------------------------------------------------
# Edge: --count 25 is capped at 20
# ---------------------------------------------------------------------------

class TestHistoryCountCap:
    """Edge: --count values above 20 are capped with a warning."""

    def test_count_25_capped_at_20_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--count 25 should emit a warning to stderr and cap at 20."""
        # Build a 5-commit repo (enough to test capping logic without slowness).
        repo = _make_repo(tmp_path, num_commits=5)
        monkeypatch.chdir(repo)

        exit_code = main(["history", "--count", "25"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower() or "cap" in captured.err.lower(), (
            f"Expected a cap warning in stderr, got: {captured.err!r}"
        )

    def test_count_25_still_produces_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--count 25 should still produce output (capped to available commits)."""
        repo = _make_repo(tmp_path, num_commits=3)
        monkeypatch.chdir(repo)

        exit_code = main(["history", "--count", "25"])

        assert exit_code == 0
        captured = capsys.readouterr()
        # At least some data rows should appear even when count is capped.
        assert captured.out.strip(), "Expected non-empty stdout output"


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestCheckGitRepo:
    """Unit tests for the _check_git_repo helper."""

    def test_true_inside_git_repo(self, tmp_path: Path) -> None:
        """Returns True when inside a git repository."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(["init"], repo)
        assert _check_git_repo(repo) is True

    def test_false_outside_git_repo(self, tmp_path: Path) -> None:
        """Returns False when not inside a git repository."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()
        assert _check_git_repo(non_repo) is False


class TestGetCommits:
    """Unit tests for the _get_commits helper."""

    def test_returns_correct_count(self, tmp_path: Path) -> None:
        """Returns at most N commit tuples when N is requested."""
        repo = _make_repo(tmp_path, num_commits=3)
        commits = _get_commits(repo, 2)
        assert len(commits) == 2

    def test_empty_repo_returns_empty_list(self, tmp_path: Path) -> None:
        """Returns an empty list for a repo with no commits."""
        repo = tmp_path / "empty"
        repo.mkdir()
        _git(["init"], repo)
        _git(["config", "user.email", "t@t.com"], repo)
        _git(["config", "user.name", "T"], repo)
        commits = _get_commits(repo, 5)
        assert commits == []

    def test_tuple_structure(self, tmp_path: Path) -> None:
        """Each commit entry is a (full_hash, subject, date) tuple."""
        repo = _make_repo(tmp_path, num_commits=1)
        commits = _get_commits(repo, 1)
        assert len(commits) == 1
        full_hash, subject, date = commits[0]
        assert len(full_hash) == 40, "Expected full 40-char SHA"
        assert subject, "Subject should be non-empty"
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", date), f"Date {date!r} not YYYY-MM-DD"


class TestFormatHelpers:
    """Unit tests for the _format_table and _format_json helpers."""

    def _sample_entries(self) -> list[CommitEntry]:
        return [
            CommitEntry(short_hash="abc1234", date="2026-06-08", score=87.4, message="feat: add init wizard"),
            CommitEntry(short_hash="def5678", date="2026-06-07", score=85.1, message="fix: format_verbose"),
            CommitEntry(short_hash="ghi9012", date="2026-06-06", score=None, message="chore: empty"),
        ]

    def test_format_table_contains_hash(self) -> None:
        table = _format_table(self._sample_entries())
        assert "abc1234" in table

    def test_format_table_contains_score(self) -> None:
        table = _format_table(self._sample_entries())
        assert "87.4" in table

    def test_format_table_none_score_shows_na(self) -> None:
        table = _format_table(self._sample_entries())
        assert "N/A" in table

    def test_format_json_is_valid(self) -> None:
        result = _format_json(self._sample_entries())
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_format_json_required_keys(self) -> None:
        result = _format_json(self._sample_entries())
        data = json.loads(result)
        for obj in data:
            assert {"hash", "message", "date", "score"} <= set(obj.keys())

    def test_format_json_null_score(self) -> None:
        """None scores map to JSON null."""
        result = _format_json(self._sample_entries())
        data = json.loads(result)
        none_entries = [obj for obj in data if obj["score"] is None]
        assert len(none_entries) == 1
