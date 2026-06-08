"""Configuration loader and schema for AgentRepoCoach.

Uses the stdlib ``tomllib`` (Python 3.11+) to parse ``.agentrepocoach.toml``. No
PyYAML dependency: zero runtime deps is a hard supply-chain-trust constraint.

All fields in the config file are optional. ``load_config(repo_root)`` returns
a populated ``Config`` object with defaults filled in. If the file is missing
or unreadable, defaults are used.
"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Module-level guard: emit the soft-upgrade warning at most once per process
# per schema version encountered.
_warned_schemas: set[int] = set()

# Schema version — bump on breaking config changes.
# v1 → v2: Added 6th component ``bootstrap_signals`` (ARC-005). Existing
# configs that pin all five weights must add ``bootstrap_signals`` to the
# [weights] table and set ``schema_version = 2``.
CURRENT_SCHEMA_VERSION = 2

# Default component weights. Derived from methodology research: navigability
# and error quality dominate because agents fail fastest on missing entry
# points and unactionable errors. Rebalanced in v2 to accommodate the new
# bootstrap_signals component (navigability 0.25→0.22, error_quality 0.25→0.22,
# decision_queryability 0.20→0.18, test_quality 0.15→0.13, module_hygiene 0.15→0.13).
DEFAULT_WEIGHTS: dict[str, float] = {
    "navigability": 0.22,
    "error_quality": 0.22,
    "decision_queryability": 0.18,
    "test_quality": 0.13,
    "module_hygiene": 0.13,
    "bootstrap_signals": 0.12,
}

_PRIVATE_INTERNAL_WEIGHTS: dict[str, float] = {
    **DEFAULT_WEIGHTS,
    "bootstrap_signals": 0.06,
    "navigability": 0.28,
}
_warned_repo_type_applied: bool = False

DEFAULT_EXCLUDES: tuple[str, ...] = (
    "node_modules/**",
    "vendor/**",
    "third_party/**",
    "**/bin/**",
    "**/obj/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/.tox/**",
    "**/*.Designer.*",
    "**/*.g.*",
)

# Language-neutral files allowed at repo root without counting as "stale".
DEFAULT_ROOT_ALLOWLIST: tuple[str, ...] = (
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    "LICENSE",
    "NOTICE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
)


@dataclass(frozen=True)
class ThresholdConfig:
    """Numeric thresholds shared across components."""
    god_file_loc: int = 800
    adr_min_count: int = 20
    doc_comment_min_coverage_pct: float = 90.0
    cli_manifest_min_commands: int = 20
    cli_manifest_fresh_days: int = 7
    cli_manifest_stale_days: int = 14
    root_stale_max_penalty_count: int = 5
    # Threat-model hardening constants (see SECURITY.md).
    max_file_bytes: int = 10_485_760  # 10 MB
    follow_symlinks: bool = False


@dataclass(frozen=True)
class DecisionQueryabilityConfig:
    """Settings for the decision_queryability component."""
    inline_ref_patterns: tuple[str, ...] = ("ADR-\\d+",)
    adr_index: str = ""


@dataclass(frozen=True)
class ErrorQualityConfig:
    """Settings for the error_quality component."""
    domain_exception_base: str = ""
    domain_exception_types: tuple[str, ...] = ()
    hint_marker: str = "Suggested fix:"


@dataclass(frozen=True)
class TestQualityConfig:
    """Settings for the test_quality component."""
    fixture_duplication_patterns: tuple[str, ...] = ()
    helpers_full_count: int = 10


@dataclass(frozen=True)
class ModuleHygieneConfig:
    """Settings for the module_hygiene component."""
    architecture_doc_fresh_days: int = 60
    internal_visibility_full_ratio: float = 0.10


@dataclass(frozen=True)
class BootstrapSignalsConfig:
    """Settings for the bootstrap_signals component."""
    install_command_patterns: tuple[str, ...] = (
        "pip install",
        "uv pip",
        "npm install",
        "npm ci",
        "yarn install",
        "cargo install",
        "cargo build",
        "go install",
        "go get",
        "dotnet add",
        "dotnet restore",
    )
    test_command_patterns: tuple[str, ...] = (
        "pytest",
        "npm test",
        "npm run test",
        "go test",
        "cargo test",
        "dotnet test",
        "make test",
        "mvn test",
        "gradle test",
    )
    ci_workflow_globs: tuple[str, ...] = (
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".gitlab-ci.yml",
        ".circleci/config.yml",
    )
    readme_head_lines: int = 100


@dataclass(frozen=True)
class PathConfig:
    """File and directory paths used by scoring components."""
    agents_md: str = "AGENTS.md"
    codebase_map: str = "docs/codebase-map.md"
    cli_manifest: str = "docs/cli-manifest.json"
    adr_dir: str = "docs/adr/"
    architecture_doc: str = "docs/architecture.md"
    test_helpers_dir: str = "auto"
    production_modules: tuple[str, ...] = ("auto",)


@dataclass(frozen=True)
class Config:
    """Fully-populated AgentRepoCoach configuration."""
    schema_version: int = CURRENT_SCHEMA_VERSION
    language: str = "auto"
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    paths: PathConfig = field(default_factory=PathConfig)
    exclude: tuple[str, ...] = DEFAULT_EXCLUDES
    root_allowlist: tuple[str, ...] = DEFAULT_ROOT_ALLOWLIST
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    decision_queryability: DecisionQueryabilityConfig = field(default_factory=DecisionQueryabilityConfig)
    error_quality: ErrorQualityConfig = field(default_factory=ErrorQualityConfig)
    test_quality: TestQualityConfig = field(default_factory=TestQualityConfig)
    module_hygiene: ModuleHygieneConfig = field(default_factory=ModuleHygieneConfig)
    bootstrap_signals: BootstrapSignalsConfig = field(default_factory=BootstrapSignalsConfig)
    repo_type: str = ""


def _warn_repo_type_once() -> None:
    global _warned_repo_type_applied
    if _warned_repo_type_applied:
        return
    _warned_repo_type_applied = True
    print(
        'agentrepocoach: INFO: repo_type = "private-internal" is set: '
        "bootstrap_signals weight adjusted 0.12 → 0.06; "
        "navigability adjusted 0.22 → 0.28. "
        "Cross-repo comparisons with repos that do not set repo_type use "
        "different baselines. See docs/configuration.md.",
        file=sys.stderr,
    )


class ConfigError(ValueError):
    """Raised when a config file exists but fails validation."""


def load_config(repo_root: Path, config_path: Path | None = None) -> Config:
    """Load ``.agentrepocoach.toml`` from ``repo_root`` (or an explicit path).

    Missing file -> returns the default Config.
    Malformed file -> raises ConfigError.
    """
    path = config_path if config_path is not None else (repo_root / ".agentrepocoach.toml")
    if not path.is_file():
        return Config()

    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        msg = f"Failed to parse {path}: {exc}."
        raise ConfigError(f"{msg} Check that the file is valid TOML. See docs/configuration.md for syntax examples.") from exc

    return _build_config_from_dict(raw)


def _build_config_from_dict(raw: dict[str, Any]) -> Config:
    """Merge a parsed TOML dict into a Config with defaults applied."""
    schema_version = int(raw.get("schema_version", CURRENT_SCHEMA_VERSION))
    if schema_version > CURRENT_SCHEMA_VERSION:
        msg = f"Unsupported schema_version {schema_version}. This tool supports schema_version {CURRENT_SCHEMA_VERSION}."
        raise ConfigError(f"{msg} Try updating agentrepocoach or check the config file format at docs/configuration.md.")

    if schema_version < CURRENT_SCHEMA_VERSION:
        if schema_version not in _warned_schemas:
            _warned_schemas.add(schema_version)
            print(
                f"agentrepocoach: WARNING: .agentrepocoach.toml uses schema_version {schema_version}; "
                f"this tool ships schema_version {CURRENT_SCHEMA_VERSION}. Auto-upgrading in-memory; "
                f"please bump your config and rebalance [weights]. See docs/configuration.md.",
                file=sys.stderr,
            )

    repo_type = str(raw.get("repo_type", ""))
    base_weights = dict(
        _PRIVATE_INTERNAL_WEIGHTS if repo_type == "private-internal" else DEFAULT_WEIGHTS
    )
    weights = base_weights
    weights.update(raw.get("weights", {}))
    if repo_type == "private-internal":
        _warn_repo_type_once()

    if schema_version < CURRENT_SCHEMA_VERSION:
        current_sum = sum(weights.values())
        if abs(current_sum - 1.0) > 0.01:
            for k in weights:
                weights[k] = weights[k] / current_sum

    _validate_weights(weights)

    return Config(
        schema_version=schema_version,
        language=str(raw.get("language", "auto")),
        weights=weights,
        paths=_build_path_config(raw.get("paths", {})),
        exclude=tuple(raw.get("exclude", DEFAULT_EXCLUDES)),
        root_allowlist=tuple(raw.get("root_allowlist", DEFAULT_ROOT_ALLOWLIST)),
        thresholds=_build_threshold_config(raw.get("thresholds", {})),
        decision_queryability=_build_decision_queryability_config(
            raw.get("decision_queryability", {}),
        ),
        error_quality=_build_error_quality_config(raw.get("error_quality", {})),
        test_quality=_build_test_quality_config(raw.get("test_quality", {})),
        module_hygiene=_build_module_hygiene_config(raw.get("module_hygiene", {})),
        bootstrap_signals=_build_bootstrap_signals_config(raw.get("bootstrap_signals", {})),
        repo_type=repo_type,
    )


def _validate_weights(weights: dict[str, float]) -> None:
    """Ensure every component has a weight and they sum to ~1.0."""
    missing = set(DEFAULT_WEIGHTS) - set(weights)
    if missing:
        msg = f"Missing component weights: {sorted(missing)}."
        raise ConfigError(f"{msg} Check that [weights] in .agentrepocoach.toml includes all six components. See docs/configuration.md.")
    total = sum(weights[name] for name in DEFAULT_WEIGHTS)
    if abs(total - 1.0) > 0.01:
        msg = f"Component weights must sum to 1.0 (got {total:.3f})."
        raise ConfigError(f"{msg} Check the [weights] section in .agentrepocoach.toml and ensure the six values add up to exactly 1.0.")


def _build_path_config(raw: dict[str, Any]) -> PathConfig:
    production = raw.get("production_modules", ("auto",))
    if isinstance(production, str):
        production = (production,)
    return PathConfig(
        agents_md=str(raw.get("agents_md", "AGENTS.md")),
        codebase_map=str(raw.get("codebase_map", "docs/codebase-map.md")),
        cli_manifest=str(raw.get("cli_manifest", "docs/cli-manifest.json")),
        adr_dir=str(raw.get("adr_dir", "docs/adr/")),
        architecture_doc=str(raw.get("architecture_doc", "docs/architecture.md")),
        test_helpers_dir=str(raw.get("test_helpers_dir", "auto")),
        production_modules=tuple(production),
    )


def _build_threshold_config(raw: dict[str, Any]) -> ThresholdConfig:
    return ThresholdConfig(
        god_file_loc=int(raw.get("god_file_loc", 800)),
        adr_min_count=int(raw.get("adr_min_count", 20)),
        doc_comment_min_coverage_pct=float(raw.get("doc_comment_min_coverage_pct", 90.0)),
        cli_manifest_min_commands=int(raw.get("cli_manifest_min_commands", 20)),
        cli_manifest_fresh_days=int(raw.get("cli_manifest_fresh_days", 7)),
        cli_manifest_stale_days=int(raw.get("cli_manifest_stale_days", 14)),
        root_stale_max_penalty_count=int(raw.get("root_stale_max_penalty_count", 5)),
        max_file_bytes=int(raw.get("max_file_bytes", 10_485_760)),
        follow_symlinks=bool(raw.get("follow_symlinks", False)),
    )


def _build_decision_queryability_config(raw: dict[str, Any]) -> DecisionQueryabilityConfig:
    return DecisionQueryabilityConfig(
        inline_ref_patterns=tuple(raw.get("inline_ref_patterns", ("ADR-\\d+",))),
        adr_index=str(raw.get("adr_index", "")),
    )


def _build_error_quality_config(raw: dict[str, Any]) -> ErrorQualityConfig:
    return ErrorQualityConfig(
        domain_exception_base=str(raw.get("domain_exception_base", "")),
        domain_exception_types=tuple(raw.get("domain_exception_types", ())),
        hint_marker=str(raw.get("hint_marker", "Suggested fix:")),
    )


def _build_test_quality_config(raw: dict[str, Any]) -> TestQualityConfig:
    return TestQualityConfig(
        fixture_duplication_patterns=tuple(raw.get("fixture_duplication_patterns", ())),
        helpers_full_count=int(raw.get("helpers_full_count", 10)),
    )


def _build_module_hygiene_config(raw: dict[str, Any]) -> ModuleHygieneConfig:
    return ModuleHygieneConfig(
        architecture_doc_fresh_days=int(raw.get("architecture_doc_fresh_days", 60)),
        internal_visibility_full_ratio=float(raw.get("internal_visibility_full_ratio", 0.10)),
    )


def _build_bootstrap_signals_config(raw: dict[str, Any]) -> BootstrapSignalsConfig:
    install_patterns = raw.get("install_command_patterns")
    test_patterns = raw.get("test_command_patterns")
    ci_globs = raw.get("ci_workflow_globs")
    defaults = BootstrapSignalsConfig()
    return BootstrapSignalsConfig(
        install_command_patterns=tuple(install_patterns) if install_patterns is not None else defaults.install_command_patterns,
        test_command_patterns=tuple(test_patterns) if test_patterns is not None else defaults.test_command_patterns,
        ci_workflow_globs=tuple(ci_globs) if ci_globs is not None else defaults.ci_workflow_globs,
        readme_head_lines=int(raw.get("readme_head_lines", defaults.readme_head_lines)),
    )
