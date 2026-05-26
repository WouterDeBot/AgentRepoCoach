"""Config loader tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentrepocoach.config import (
    CURRENT_SCHEMA_VERSION,
    Config,
    ConfigError,
    load_config,
)


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.schema_version == CURRENT_SCHEMA_VERSION
    assert config.language == "auto"
    assert sum(config.weights.values()) == pytest.approx(1.0)


def test_load_config_parses_custom_weights(tmp_path: Path) -> None:
    (tmp_path / ".agentrepocoach.toml").write_text(
        """
schema_version = 2
language = "python"

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12
""",
    )
    config = load_config(tmp_path)
    assert config.language == "python"
    assert config.weights["navigability"] == 0.22
    assert config.weights["module_hygiene"] == 0.13


def test_load_config_rejects_unbalanced_weights(tmp_path: Path) -> None:
    (tmp_path / ".agentrepocoach.toml").write_text(
        """
[weights]
navigability = 0.50
error_quality = 0.25
decision_queryability = 0.20
test_quality = 0.15
module_hygiene = 0.15
bootstrap_signals = 0.12
""",
    )
    with pytest.raises(ConfigError, match="weights must sum to 1.0"):
        load_config(tmp_path)


def test_load_config_rejects_unknown_schema_version(tmp_path: Path) -> None:
    (tmp_path / ".agentrepocoach.toml").write_text("schema_version = 99\n")
    with pytest.raises(ConfigError, match="Unsupported schema_version"):
        load_config(tmp_path)


def test_load_config_rejects_malformed_toml(tmp_path: Path) -> None:
    (tmp_path / ".agentrepocoach.toml").write_text("not = valid = toml")
    with pytest.raises(ConfigError, match="Failed to parse"):
        load_config(tmp_path)


def test_load_config_error_quality_defaults() -> None:
    config = Config()
    assert config.error_quality.domain_exception_types == ()
    assert config.error_quality.hint_marker == "Suggested fix:"
    assert config.error_quality.domain_exception_base == ""


def test_load_config_fixture_duplication_defaults_empty() -> None:
    config = Config()
    assert config.test_quality.fixture_duplication_patterns == ()


def test_load_config_inline_refs_defaults_adr() -> None:
    config = Config()
    assert config.decision_queryability.inline_ref_patterns == ("ADR-\\d+",)


def test_load_config_thresholds_hardening_defaults() -> None:
    config = Config()
    assert config.thresholds.follow_symlinks is False
    assert config.thresholds.max_file_bytes == 10_485_760


def test_load_config_explicit_domain_types(tmp_path: Path) -> None:
    (tmp_path / ".agentrepocoach.toml").write_text(
        """
[error_quality]
domain_exception_types = ["FooError", "BarError"]
""",
    )
    config = load_config(tmp_path)
    assert config.error_quality.domain_exception_types == ("FooError", "BarError")


# --- ARC-005: schema v2 migration tests ---

def test_load_config_v1_raises_with_migration_recipe(tmp_path: Path) -> None:
    """AC-03/AC-04: loading a v1 config raises ConfigError with migration recipe."""
    (tmp_path / ".agentrepocoach.toml").write_text("schema_version = 1\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path)
    msg = str(exc_info.value)
    assert "Unsupported schema_version 1" in msg
    assert "schema_version = 2" in msg
    assert "bootstrap_signals" in msg


def test_load_config_v2_default_has_six_weights() -> None:
    """AC-03/AC-04: default Config (no file) has 6 weights summing to 1.0."""
    config = Config()
    assert config.schema_version == 2
    assert "bootstrap_signals" in config.weights
    assert len(config.weights) == 6
    assert sum(config.weights.values()) == pytest.approx(1.0, abs=0.01)


def test_load_config_bootstrap_signals_defaults() -> None:
    """AC-03: BootstrapSignalsConfig defaults are populated correctly."""
    config = Config()
    assert "pytest" in config.bootstrap_signals.test_command_patterns
    assert "pip install" in config.bootstrap_signals.install_command_patterns
    assert config.bootstrap_signals.readme_head_lines == 100
