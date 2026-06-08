"""Component tests — each component against a fixture repo + the orchestrator."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentrepocoach.adapters import CSharpAdapter, PythonAdapter, detect_primary
from agentrepocoach.components import (
    compute_bootstrap_signals,
    compute_decision_queryability,
    compute_error_quality,
    compute_module_hygiene,
    compute_navigability,
    compute_test_quality,
)
from agentrepocoach.compute import compute_cah
from agentrepocoach.config import Config
from agentrepocoach.scoring import scale_linear

FIXTURES = Path(__file__).parent / "fixtures"


def test_scale_linear_basic() -> None:
    assert scale_linear(0, 0, 10, 100) == 0
    assert scale_linear(10, 0, 10, 100) == 100
    assert scale_linear(5, 0, 10, 100) == 50


def test_scale_linear_inverted() -> None:
    assert scale_linear(0, 10, 0, 100) == 100
    assert scale_linear(10, 10, 0, 100) == 0
    assert scale_linear(5, 10, 0, 100) == 50


def test_scale_linear_clamps_out_of_range() -> None:
    assert scale_linear(-5, 0, 10, 100) == 0
    assert scale_linear(100, 0, 10, 100) == 100


def test_navigability_csharp_fixture_full_credit(csharp_fixture: Path) -> None:
    result = compute_navigability(csharp_fixture, Config(), CSharpAdapter())
    agents = result["breakdown"]["agents_md"]
    assert agents["exists"] is True
    assert agents["missing_links"] == []
    assert agents["score"] == 30
    manifest = result["breakdown"]["cli_manifest"]
    assert manifest["command_count"] == 21
    assert manifest["score"] == 20
    codebase_map = result["breakdown"]["codebase_map"]
    assert codebase_map["matched_projects"] == codebase_map["total_projects"]


def test_error_quality_csharp_fixture_has_user_defined_throws(csharp_fixture: Path) -> None:
    result = compute_error_quality(csharp_fixture, Config(), CSharpAdapter())
    hint = result["breakdown"]["hint_coverage"]
    subclass = result["breakdown"]["exception_subclass_ratio"]
    assert hint["total_sites"] >= 2
    assert subclass["ratio"] == 1.0


def test_decision_queryability_csharp_fixture_has_adrs(csharp_fixture: Path) -> None:
    result = compute_decision_queryability(csharp_fixture, Config(), CSharpAdapter())
    adr = result["breakdown"]["adr_catalog"]
    assert adr["valid_count"] == 5
    # 5 / 20 -> 25% of full credit on 60 pt budget -> 15.
    assert adr["score"] == pytest.approx(15.0, abs=0.1)


def test_test_quality_csharp_fixture_has_mse_naming(csharp_fixture: Path) -> None:
    result = compute_test_quality(csharp_fixture, Config(), CSharpAdapter())
    naming = result["breakdown"]["naming_convention"]
    assert naming["total_methods"] >= 3
    assert naming["matching_methods"] == naming["total_methods"]
    helpers = result["breakdown"]["helper_files"]
    assert helpers["helper_count"] >= 1
    duplication = result["breakdown"]["fixture_duplication"]
    # No fixture_duplication_patterns configured -> full credit.
    assert duplication["score"] == 30


def test_module_hygiene_csharp_fixture_has_internal_visibility(csharp_fixture: Path) -> None:
    result = compute_module_hygiene(csharp_fixture, Config(), CSharpAdapter())
    internal = result["breakdown"]["internal_visibility"]
    assert internal["total_files"] >= 1
    assert internal["internal_files"] >= 1
    arch = result["breakdown"]["architecture_doc"]
    assert arch["exists"] is True


def test_compute_cah_csharp_fixture_produces_valid_result(csharp_fixture: Path) -> None:
    result = compute_cah(csharp_fixture)
    assert result["schema_version"] == 2
    assert result["generator"].startswith("agentrepocoach ")
    assert result["language"] == "csharp"
    assert 0.0 <= result["total"] <= 100.0
    assert set(result["components"].keys()) == {
        "navigability",
        "error_quality",
        "decision_queryability",
        "test_quality",
        "module_hygiene",
        "bootstrap_signals",
    }


def test_compute_cah_python_fixture_produces_valid_result(python_fixture: Path) -> None:
    result = compute_cah(python_fixture)
    assert result["language"] == "python"
    assert 0.0 <= result["total"] <= 100.0


def test_compute_cah_error_quality_reallocated_weights(csharp_fixture: Path) -> None:
    """decision_queryability should sum to 100 after MCP sub-score removal."""
    result = compute_cah(csharp_fixture)
    dq = result["components"]["decision_queryability"]
    max_score = sum(sub["max"] for sub in dq["breakdown"].values())
    assert max_score == 100  # 60 (adr_catalog) + 40 (inline_ref_resolution)


# --- ARC-005: CI-signal sub-score tests (AC-01) ---

# --- ARC-005: README-quality sub-score tests (AC-02) ---

def test_readme_quality_absent_scores_zero(tmp_path: Path) -> None:
    """AC-02: repo with no README scores 0 on readme_quality."""
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(tmp_path, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    assert rq["score"] == 0
    assert rq["install_found"] is False
    assert rq["test_found"] is False


def test_readme_quality_install_only_scores_partial(tmp_path: Path) -> None:
    """AC-02: README with install command only scores ~50% of readme_quality max."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Project\n\n## Install\n\n```bash\npip install myproject\n```\n",
        encoding="utf-8",
    )
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(tmp_path, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    # 25 pts for install found, 0 for no test command
    assert rq["score"] == 25
    assert rq["install_found"] is True
    assert rq["test_found"] is False


def test_readme_quality_full_scores_max() -> None:
    """AC-02: README with both install and test commands scores >=80% of max (50 pts)."""
    fixture = FIXTURES / "sample-readme-quality"
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(fixture, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    # 25 pts install + 25 pts test = 50 (100% of max)
    assert rq["score"] >= 40  # >= 80% of 50
    assert rq["install_found"] is True
    assert rq["test_found"] is True


# --- ARC-005: CI-signal sub-score tests (AC-01) ---

def test_readme_quality_note_when_install_missing(tmp_path: Path) -> None:
    """GH-009 Bug 2: note surfaced in breakdown when install not found."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Project\n\n## Usage\n\n```bash\npytest\n```\n",
        encoding="utf-8",
    )
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(tmp_path, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    assert rq["install_found"] is False
    assert "note" in rq
    assert "scanned first" in rq["note"]
    assert ".agentrepocoach.toml" in rq["note"]


def test_readme_quality_note_when_test_missing(tmp_path: Path) -> None:
    """GH-009 Bug 2: note surfaced in breakdown when test not found."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Project\n\n## Install\n\n```bash\npip install myproject\n```\n",
        encoding="utf-8",
    )
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(tmp_path, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    assert rq["test_found"] is False
    assert "note" in rq
    assert "scanned first" in rq["note"]


def test_readme_quality_no_note_when_both_found() -> None:
    """GH-009 Bug 2: no note when both install and test commands are found."""
    fixture = FIXTURES / "sample-readme-quality"
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(fixture, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    assert rq["install_found"] is True
    assert rq["test_found"] is True
    assert "note" not in rq


def test_readme_quality_note_reflects_custom_head_lines(tmp_path: Path) -> None:
    """GH-009 Bug 2: note reflects readme_head_lines config value."""
    import dataclasses

    readme = tmp_path / "README.md"
    readme.write_text("# Project\n", encoding="utf-8")
    base = Config()
    bsc = dataclasses.replace(base.bootstrap_signals, readme_head_lines=200)
    config = dataclasses.replace(base, bootstrap_signals=bsc)
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(tmp_path, config, adapter)
    rq = result["breakdown"]["readme_quality"]
    assert "note" in rq
    assert "200" in rq["note"]


# --- ARC-005: CI-signal sub-score tests (AC-01) ---

def test_ci_signal_absent_scores_zero() -> None:
    """AC-01: repo with no CI artifacts scores 0 on ci_signal."""
    fixture = FIXTURES / "sample-ci-signal-absent"
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(fixture, config, adapter)
    ci = result["breakdown"]["ci_signal"]
    assert ci["score"] == 0
    assert ci["workflows_found"] == 0


def test_ci_signal_present_no_pr_trigger_scores_partial() -> None:
    """AC-01: repo with CI workflow but no pull_request trigger scores ~30/50."""
    fixture = FIXTURES / "sample-ci-signal-no-pr"
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(fixture, config, adapter)
    ci = result["breakdown"]["ci_signal"]
    # 30 pts for having a workflow, 0 for no PR trigger -> 60% of 50 max
    assert ci["score"] == 30
    assert ci["pr_trigger"] is False
    assert ci["workflows_found"] >= 1


def test_ci_signal_present_with_pr_trigger_scores_full() -> None:
    """AC-01: repo with CI workflow with pull_request trigger scores >=50% max (50 pts)."""
    fixture = FIXTURES / "sample-ci-signal-good"
    config = Config()
    adapter = PythonAdapter()
    result = compute_bootstrap_signals(fixture, config, adapter)
    ci = result["breakdown"]["ci_signal"]
    # Full score: 30 + 20 = 50
    assert ci["score"] == 50
    assert ci["pr_trigger"] is True
    assert ci["workflows_found"] >= 1
