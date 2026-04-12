"""Adapter tests — detection, discovery, and scanning against fixture repos."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentrepocoach.adapters import (
    CSharpAdapter,
    NoAdapterError,
    PythonAdapter,
    TypeScriptAdapter,
    detect_primary,
    get_adapter_by_name,
)
from agentrepocoach.adapters.base import NotSupportedError


def test_detect_primary_picks_csharp_for_sln_repo(csharp_fixture: Path) -> None:
    adapter = detect_primary(csharp_fixture)
    assert adapter.name == "csharp"


def test_detect_primary_picks_python_for_pyproject_repo(python_fixture: Path) -> None:
    adapter = detect_primary(python_fixture)
    assert adapter.name == "python"


def test_detect_primary_raises_on_empty_repo(empty_fixture: Path) -> None:
    with pytest.raises(NoAdapterError):
        detect_primary(empty_fixture)


def test_csharp_adapter_finds_production_and_test_files(csharp_fixture: Path) -> None:
    adapter = CSharpAdapter()
    prod = adapter.find_production_files(csharp_fixture)
    tests = adapter.find_test_files(csharp_fixture)
    assert any(p.name == "SampleService.cs" for p in prod)
    assert not any(p.name == "SampleServiceTests.cs" for p in prod)
    assert any(p.name == "SampleServiceTests.cs" for p in tests)


def test_csharp_adapter_finds_production_modules(csharp_fixture: Path) -> None:
    adapter = CSharpAdapter()
    modules = adapter.find_production_modules(csharp_fixture)
    assert "Sample.Core" in modules
    assert "Sample.Tests" not in modules


def test_csharp_adapter_scans_throw_sites_with_hints(csharp_fixture: Path) -> None:
    adapter = CSharpAdapter()
    prod = adapter.find_production_files(csharp_fixture)
    sites = adapter.scan_throw_sites(
        prod,
        hint_marker="Suggested fix:",
        domain_exception_types={"SampleException", "SampleValidationException"},
    )
    assert len(sites) >= 2
    assert all(site.exception_type == "SampleValidationException" for site in sites)
    assert any(site.has_fix_hint for site in sites)
    assert all(site.is_user_defined for site in sites)


def test_csharp_adapter_scans_declarations_with_doc_comments(csharp_fixture: Path) -> None:
    adapter = CSharpAdapter()
    prod = adapter.find_production_files(csharp_fixture)
    declarations = adapter.scan_declarations(prod)
    names = {d.name for d in declarations}
    assert "SampleService" in names
    assert "SampleInternalHelper" in names
    service_decl = next(d for d in declarations if d.name == "SampleService")
    assert service_decl.visibility == "public"
    assert service_decl.has_doc_comment is True
    internal_decl = next(d for d in declarations if d.name == "SampleInternalHelper")
    assert internal_decl.visibility == "internal"


def test_csharp_adapter_finds_test_methods(csharp_fixture: Path) -> None:
    adapter = CSharpAdapter()
    test_files = adapter.find_test_files(csharp_fixture)
    methods = adapter.find_test_methods(test_files)
    assert any(name == "DoWork_PositiveInput_ReturnsDouble" for _, name in methods)


def test_python_adapter_finds_production_files(python_fixture: Path) -> None:
    adapter = PythonAdapter()
    prod = adapter.find_production_files(python_fixture)
    assert any(p.name == "service.py" for p in prod)
    # Production files should be under src/ not under the repo's own tests/ dir.
    rel_parts = [p.relative_to(python_fixture).parts for p in prod]
    assert not any(parts[0] == "tests" for parts in rel_parts)


def test_python_adapter_finds_test_files(python_fixture: Path) -> None:
    adapter = PythonAdapter()
    tests = adapter.find_test_files(python_fixture)
    assert any(p.name == "test_sample_service.py" for p in tests)


def test_python_adapter_scans_raise_sites(python_fixture: Path) -> None:
    adapter = PythonAdapter()
    prod = adapter.find_production_files(python_fixture)
    sites = adapter.scan_throw_sites(
        prod,
        hint_marker="Suggested fix:",
        domain_exception_types={"SampleError", "SampleValidationError"},
    )
    assert len(sites) >= 2
    assert any(s.exception_type == "SampleValidationError" for s in sites)


def test_python_adapter_scans_declarations(python_fixture: Path) -> None:
    adapter = PythonAdapter()
    prod = adapter.find_production_files(python_fixture)
    declarations = adapter.scan_declarations(prod)
    names = {d.name for d in declarations}
    assert "SampleService" in names
    assert "SampleError" in names
    # Private/dunder names start with underscore.
    assert any(d.name == "_internal_helper" and d.visibility == "private" for d in declarations)


def test_typescript_stub_raises_not_supported(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    adapter = TypeScriptAdapter()
    assert adapter.detect(tmp_path) > 0.0
    with pytest.raises(NotSupportedError):
        adapter.find_production_files(tmp_path)


def test_get_adapter_by_name_unknown_raises() -> None:
    with pytest.raises(NoAdapterError):
        get_adapter_by_name("cobol")
