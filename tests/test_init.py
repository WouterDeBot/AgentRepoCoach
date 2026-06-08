"""Tests for the ``agentrepocoach init`` subcommand (XPL-006).

AC-01: init in an empty directory creates a valid .agentrepocoach.toml that
       load_config() accepts without ConfigError.
AC-02: The created file contains schema_version = 2 and all 6 weight keys.
AC-03: Running init twice exits non-zero (does NOT overwrite existing file).
AC-04: init --repo-type private-internal sets repo_type in the output file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agentrepocoach.cli import main
from agentrepocoach.config import (
    CURRENT_SCHEMA_VERSION,
    DEFAULT_WEIGHTS,
    ConfigError,
    load_config,
)
from agentrepocoach.init_cmd import build_toml_content, run_init


class TestInitCreatesValidConfig:
    """AC-01: init creates a file that load_config() accepts without ConfigError."""

    def test_creates_config_file(self, tmp_path: Path) -> None:
        """A fresh directory should get a .agentrepocoach.toml after init."""
        output = tmp_path / ".agentrepocoach.toml"
        exit_code = run_init(output, repo_type="")
        assert exit_code == 0
        assert output.is_file(), "Config file was not created"

    def test_created_config_loads_without_error(self, tmp_path: Path) -> None:
        """load_config() must not raise ConfigError on the generated file."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        # load_config() with an explicit path to the generated file
        config = load_config(tmp_path, config_path=output)
        assert config is not None

    def test_init_via_cli_main(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """main(['init']) in a tmp_path should return 0 and create the file."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["init"])
        assert exit_code == 0
        assert (tmp_path / ".agentrepocoach.toml").is_file()


class TestInitConfigContents:
    """AC-02: created file must have schema_version = 2 and all 6 weight keys."""

    def test_schema_version_present(self, tmp_path: Path) -> None:
        """schema_version must equal CURRENT_SCHEMA_VERSION (2)."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        content = output.read_text()
        assert f"schema_version = {CURRENT_SCHEMA_VERSION}" in content

    def test_all_six_weight_keys_present(self, tmp_path: Path) -> None:
        """All six component weight keys must appear in the generated TOML."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        content = output.read_text()
        for key in DEFAULT_WEIGHTS:
            assert key in content, f"Weight key '{key}' missing from generated config"

    def test_weights_section_header_present(self, tmp_path: Path) -> None:
        """[weights] section header must be present."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        content = output.read_text()
        assert "[weights]" in content

    def test_generated_config_passes_validation(self, tmp_path: Path) -> None:
        """load_config must parse the file and weights must not raise ConfigError."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        # If this raises ConfigError the test fails automatically.
        config = load_config(tmp_path, config_path=output)
        assert config.schema_version == CURRENT_SCHEMA_VERSION
        # All six weights must be present and sum to ~1.0.
        for key in DEFAULT_WEIGHTS:
            assert key in config.weights
        weight_sum = sum(config.weights.values())
        assert abs(weight_sum - 1.0) <= 0.01, f"Weights sum to {weight_sum}, expected ~1.0"


class TestInitDoesNotOverwrite:
    """AC-03: second init call must exit non-zero and not overwrite the file."""

    def test_second_call_exits_nonzero(self, tmp_path: Path) -> None:
        """Running init when the file exists returns exit code 1."""
        output = tmp_path / ".agentrepocoach.toml"
        first = run_init(output, repo_type="")
        assert first == 0
        second = run_init(output, repo_type="")
        assert second != 0, "Second init call should have exited non-zero"

    def test_second_call_does_not_overwrite(self, tmp_path: Path) -> None:
        """File content must be unchanged after the second (rejected) init call."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        original_content = output.read_text()
        # Modify the file so we can detect an overwrite.
        output.write_text(original_content + "\n# sentinel\n", encoding="utf-8")
        run_init(output, repo_type="")
        assert "# sentinel" in output.read_text(), (
            "File was overwritten despite already existing"
        )

    def test_second_call_via_cli_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main(['init']) called twice in the same directory must exit 1 on second call."""
        monkeypatch.chdir(tmp_path)
        assert main(["init"]) == 0
        assert main(["init"]) != 0

    def test_second_call_prints_error_to_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An error message must be printed to stderr on the second call."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        capsys.readouterr()  # clear
        run_init(output, repo_type="")
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()


class TestInitRepoTypeFlag:
    """AC-04: --repo-type private-internal writes repo_type to the config file."""

    def test_repo_type_written_to_file(self, tmp_path: Path) -> None:
        """repo_type = 'private-internal' must appear in the generated TOML."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="private-internal")
        content = output.read_text()
        assert 'repo_type = "private-internal"' in content

    def test_repo_type_loads_correctly(self, tmp_path: Path) -> None:
        """load_config on a private-internal file must set config.repo_type."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="private-internal")
        config = load_config(tmp_path, config_path=output)
        assert config.repo_type == "private-internal"

    def test_repo_type_via_cli_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main(['init', '--repo-type', 'private-internal']) produces the correct file."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["init", "--repo-type", "private-internal"])
        assert exit_code == 0
        content = (tmp_path / ".agentrepocoach.toml").read_text()
        assert 'repo_type = "private-internal"' in content

    def test_default_repo_type_commented_out(self, tmp_path: Path) -> None:
        """When repo_type is not specified, the line should be a comment."""
        output = tmp_path / ".agentrepocoach.toml"
        run_init(output, repo_type="")
        content = output.read_text()
        # Active repo_type line must NOT be present (only commented form).
        assert 'repo_type = "private-internal"' not in content
        assert '# repo_type' in content

    def test_unknown_repo_type_exits_nonzero(self, tmp_path: Path) -> None:
        """An unrecognized repo_type value must return non-zero exit code."""
        output = tmp_path / ".agentrepocoach.toml"
        exit_code = run_init(output, repo_type="unknown-type")
        assert exit_code != 0
        assert not output.exists(), "File must not be created for invalid repo_type"


class TestInitCustomOutput:
    """Extra: --output flag writes to the specified path."""

    def test_custom_output_path(self, tmp_path: Path) -> None:
        """init --output <path> creates the file at the specified location."""
        custom = tmp_path / "subdir" / "my-config.toml"
        custom.parent.mkdir(parents=True)
        exit_code = run_init(custom, repo_type="")
        assert exit_code == 0
        assert custom.is_file()

    def test_custom_output_via_cli(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main(['init', '--output', path]) creates the file at the given path."""
        monkeypatch.chdir(tmp_path)
        custom = tmp_path / "custom.toml"
        exit_code = main(["init", "--output", str(custom)])
        assert exit_code == 0
        assert custom.is_file()


class TestBuildTomlContent:
    """Unit-level tests for the build_toml_content helper."""

    def test_default_content_is_valid_utf8(self) -> None:
        content = build_toml_content("")
        # Should not raise.
        content.encode("utf-8")

    def test_private_internal_activates_repo_type_line(self) -> None:
        content = build_toml_content("private-internal")
        assert 'repo_type = "private-internal"' in content

    def test_default_leaves_repo_type_commented(self) -> None:
        content = build_toml_content("")
        assert '# repo_type' in content
        # No active (uncommented) repo_type line.
        lines = [ln.strip() for ln in content.splitlines()]
        active = [ln for ln in lines if ln.startswith('repo_type =')]
        assert active == []
