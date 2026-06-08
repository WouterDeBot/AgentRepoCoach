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

def test_load_config_v1_soft_upgrade_backwards_compat(tmp_path: Path) -> None:
    """AC-03/AC-04 (updated): v1 config now soft-upgrades instead of raising.

    The old strict-raise test is replaced by the soft-upgrade tests below.
    This stub confirms the schema_version=1 path continues to load without
    a ConfigError (the new contract after D-029 operator fix-path option a).
    """
    (tmp_path / ".agentrepocoach.toml").write_text("schema_version = 1\n")
    config = load_config(tmp_path)
    assert config.schema_version == 1
    assert "bootstrap_signals" in config.weights


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


# --- D-029 soft-upgrade tests (operator fix-path option a) ---

def test_load_config_v1_schema_warns_but_loads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """D-029: v1 config emits a stderr warning but loads successfully (no raise)."""
    import agentrepocoach.config as cfg_module
    cfg_module._warned_schemas.discard(1)  # reset per-process guard for test isolation
    (tmp_path / ".agentrepocoach.toml").write_text("schema_version = 1\n")
    config = load_config(tmp_path)
    captured = capsys.readouterr()
    assert config is not None  # no ConfigError raised
    assert "schema_version 1" in captured.err
    assert "schema_version 2" in captured.err
    assert "docs/configuration.md" in captured.err


def test_load_config_v1_weights_rescale_to_sum_1(tmp_path: Path) -> None:
    """D-029: v1 toml with 5 explicit weights summing to 1.0 is rescaled to 6 keys summing to ~1.0."""
    import agentrepocoach.config as cfg_module
    cfg_module._warned_schemas.discard(1)
    toml_content = """\
schema_version = 1

[weights]
navigability = 0.25
error_quality = 0.25
decision_queryability = 0.20
test_quality = 0.15
module_hygiene = 0.15
"""
    (tmp_path / ".agentrepocoach.toml").write_text(toml_content)
    config = load_config(tmp_path)
    assert len(config.weights) == 6
    assert all(v >= 0 for v in config.weights.values())
    assert sum(config.weights.values()) == pytest.approx(1.0, abs=0.01)


def test_load_config_future_schema_still_raises(tmp_path: Path) -> None:
    """D-029: future schema_version (>2) still raises ConfigError (forward-incompat guard)."""
    (tmp_path / ".agentrepocoach.toml").write_text("schema_version = 99\n")
    with pytest.raises(ConfigError, match="Unsupported schema_version"):
        load_config(tmp_path)


def test_load_config_v2_no_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """D-029: valid v2 config emits no warning to stderr."""
    toml_content = """\
schema_version = 2

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12
"""
    (tmp_path / ".agentrepocoach.toml").write_text(toml_content)
    load_config(tmp_path)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err


# --- GH-011: repo_type private-internal weight hint tests ---

def test_repo_type_private_internal_adjusts_bootstrap_signals(tmp_path: Path) -> None:
    """repo_type=private-internal halves bootstrap_signals default weight."""
    import agentrepocoach.config as m
    m._warned_repo_type_applied = False
    (tmp_path / ".agentrepocoach.toml").write_text('repo_type = "private-internal"\n')
    config = load_config(tmp_path)
    assert config.weights["bootstrap_signals"] == pytest.approx(0.06, abs=1e-9)
    assert config.weights["navigability"] == pytest.approx(0.28, abs=1e-9)
    assert sum(config.weights.values()) == pytest.approx(1.0, abs=0.01)


def test_repo_type_private_internal_stores_on_config(tmp_path: Path) -> None:
    """Config.repo_type is set when parsed from toml."""
    import agentrepocoach.config as m
    m._warned_repo_type_applied = False
    (tmp_path / ".agentrepocoach.toml").write_text('repo_type = "private-internal"\n')
    config = load_config(tmp_path)
    assert config.repo_type == "private-internal"


def test_repo_type_private_internal_prints_advisory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """repo_type=private-internal emits INFO advisory to stderr."""
    import agentrepocoach.config as m
    m._warned_repo_type_applied = False
    (tmp_path / ".agentrepocoach.toml").write_text('repo_type = "private-internal"\n')
    load_config(tmp_path)
    err = capsys.readouterr().err
    assert "private-internal" in err
    assert "bootstrap_signals" in err
    assert "navigability" in err


def test_repo_type_private_internal_advisory_emitted_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Advisory is printed only once per process (process guard)."""
    import agentrepocoach.config as m
    m._warned_repo_type_applied = False
    toml = (tmp_path / ".agentrepocoach.toml")
    toml.write_text('repo_type = "private-internal"\n')
    load_config(tmp_path)
    load_config(tmp_path)
    err = capsys.readouterr().err
    assert err.count("private-internal") == 1


def test_repo_type_private_internal_explicit_weight_override(tmp_path: Path) -> None:
    """Explicit [weights] section overrides the private-internal default."""
    import agentrepocoach.config as m
    m._warned_repo_type_applied = False
    toml_text = """\
repo_type = "private-internal"

[weights]
navigability = 0.22
error_quality = 0.22
decision_queryability = 0.18
test_quality = 0.13
module_hygiene = 0.13
bootstrap_signals = 0.12
"""
    (tmp_path / ".agentrepocoach.toml").write_text(toml_text)
    config = load_config(tmp_path)
    # Explicit weights override the private-internal defaults
    assert config.weights["bootstrap_signals"] == pytest.approx(0.12, abs=1e-9)
    assert config.weights["navigability"] == pytest.approx(0.22, abs=1e-9)


def test_repo_type_absent_uses_default_weights(tmp_path: Path) -> None:
    """Without repo_type, default weights apply unchanged."""
    config = load_config(tmp_path)  # no toml file
    assert config.weights["bootstrap_signals"] == pytest.approx(0.12, abs=1e-9)
    assert config.weights["navigability"] == pytest.approx(0.22, abs=1e-9)
    assert config.repo_type == ""
