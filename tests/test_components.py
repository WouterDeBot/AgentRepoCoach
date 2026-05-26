"""Component tests — each component against a fixture repo + the orchestrator."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentrepocoach.adapters import CSharpAdapter, PythonAdapter, detect_primary
from agentrepocoach.components import (
    compute_decision_queryability,
    compute_error_quality,
    compute_module_hygiene,
    compute_navigability,
    compute_test_quality,
)
from agentrepocoach.compute import compute_cah
from agentrepocoach.config import Config
from agentrepocoach.scoring import scale_linear


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
