"""Adapter tests — detection, discovery, and scanning against fixture repos."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentrepocoach.adapters import (
    CSharpAdapter,
    GoAdapter,
    NoAdapterError,
    PythonAdapter,
    RustAdapter,
    TypeScriptAdapter,
    detect_primary,
    get_adapter_by_name,
)

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


def test_detect_primary_picks_typescript_for_tsconfig_repo(typescript_fixture: Path) -> None:
    adapter = detect_primary(typescript_fixture)
    assert adapter.name == "typescript"


def test_typescript_adapter_detects_tsconfig(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    adapter = TypeScriptAdapter()
    assert adapter.detect(tmp_path) == 1.0


def test_typescript_adapter_detects_package_json_with_ts_dep(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"devDependencies":{"typescript":"^5.0"}}')
    adapter = TypeScriptAdapter()
    assert adapter.detect(tmp_path) == 0.8


def test_typescript_adapter_finds_production_and_test_files(typescript_fixture: Path) -> None:
    adapter = TypeScriptAdapter()
    prod = adapter.find_production_files(typescript_fixture)
    tests = adapter.find_test_files(typescript_fixture)
    assert any(p.name == "sample-service.ts" for p in prod)
    assert not any(p.name.endswith(".test.ts") for p in prod)
    assert any(p.name == "sample-service.test.ts" for p in tests)


def test_typescript_adapter_finds_production_modules(typescript_fixture: Path) -> None:
    adapter = TypeScriptAdapter()
    modules = adapter.find_production_modules(typescript_fixture)
    assert len(modules) >= 1


def test_typescript_adapter_scans_throw_sites_with_hints(typescript_fixture: Path) -> None:
    adapter = TypeScriptAdapter()
    prod = adapter.find_production_files(typescript_fixture)
    sites = adapter.scan_throw_sites(
        prod,
        hint_marker="Suggested fix:",
        domain_exception_types={"SampleError", "SampleValidationError"},
    )
    assert len(sites) >= 2
    assert any(s.exception_type == "SampleValidationError" for s in sites)
    assert any(s.has_fix_hint for s in sites)
    assert any(s.is_user_defined for s in sites)
    # The plain Error throw should be generic.
    assert any(s.is_generic for s in sites)


def test_typescript_adapter_scans_declarations_with_doc_comments(typescript_fixture: Path) -> None:
    adapter = TypeScriptAdapter()
    prod = adapter.find_production_files(typescript_fixture)
    declarations = adapter.scan_declarations(prod)
    names = {d.name for d in declarations}
    assert "SampleService" in names
    assert "SampleError" in names
    assert "createService" in names
    # Exported declarations should be public.
    service_decl = next(d for d in declarations if d.name == "SampleService")
    assert service_decl.visibility == "public"
    assert service_decl.has_doc_comment is True
    # Non-exported declarations should be internal.
    internal_names = {d.name for d in declarations if d.visibility == "internal"}
    assert "InternalWorker" in internal_names or "_internalHelper" in internal_names


def test_typescript_adapter_finds_test_methods(typescript_fixture: Path) -> None:
    adapter = TypeScriptAdapter()
    test_files = adapter.find_test_files(typescript_fixture)
    methods = adapter.find_test_methods(test_files)
    method_names = [name for _, name in methods]
    assert any("double" in name or "positive" in name for name in method_names)
    assert len(methods) >= 2


def test_detect_primary_picks_go_for_gomod_repo(go_fixture: Path) -> None:
    adapter = detect_primary(go_fixture)
    assert adapter.name == "go"


def test_go_adapter_finds_production_and_test_files(go_fixture: Path) -> None:
    adapter = GoAdapter()
    prod = adapter.find_production_files(go_fixture)
    tests = adapter.find_test_files(go_fixture)
    assert any(p.name == "service.go" for p in prod)
    assert not any(p.name.endswith("_test.go") for p in prod)
    assert any(p.name == "service_test.go" for p in tests)


def test_go_adapter_finds_production_modules(go_fixture: Path) -> None:
    adapter = GoAdapter()
    modules = adapter.find_production_modules(go_fixture)
    assert len(modules) >= 1


def test_go_adapter_scans_throw_sites(go_fixture: Path) -> None:
    adapter = GoAdapter()
    prod = adapter.find_production_files(go_fixture)
    sites = adapter.scan_throw_sites(
        prod,
        hint_marker="Suggested fix:",
        domain_exception_types={"ValidationError"},
    )
    assert len(sites) >= 2
    # Should find custom ValidationError and generic errors.New/fmt.Errorf.
    assert any(s.exception_type == "ValidationError" for s in sites)
    assert any(s.is_generic for s in sites)
    assert any(s.is_user_defined for s in sites)
    assert any(s.has_fix_hint for s in sites)


def test_go_adapter_scans_declarations(go_fixture: Path) -> None:
    adapter = GoAdapter()
    prod = adapter.find_production_files(go_fixture)
    declarations = adapter.scan_declarations(prod)
    names = {d.name for d in declarations}
    assert "SampleService" in names
    assert "NewSampleService" in names
    assert "ValidationError" in names
    # Exported = public, unexported = internal.
    svc_decl = next(d for d in declarations if d.name == "SampleService")
    assert svc_decl.visibility == "public"
    assert svc_decl.has_doc_comment is True
    internal_names = {d.name for d in declarations if d.visibility == "internal"}
    assert "internalHelper" in internal_names


def test_go_adapter_finds_test_methods(go_fixture: Path) -> None:
    adapter = GoAdapter()
    test_files = adapter.find_test_files(go_fixture)
    methods = adapter.find_test_methods(test_files)
    method_names = [name for _, name in methods]
    assert "TestDoWork_PositiveInput_ReturnsDouble" in method_names
    assert len(methods) >= 2


def test_detect_primary_picks_rust_for_cargo_repo(rust_fixture: Path) -> None:
    adapter = detect_primary(rust_fixture)
    assert adapter.name == "rust"


def test_rust_adapter_finds_production_files(rust_fixture: Path) -> None:
    adapter = RustAdapter()
    prod = adapter.find_production_files(rust_fixture)
    assert any(p.name == "service.rs" for p in prod)
    assert any(p.name == "lib.rs" for p in prod)


def test_rust_adapter_finds_production_modules(rust_fixture: Path) -> None:
    adapter = RustAdapter()
    modules = adapter.find_production_modules(rust_fixture)
    assert len(modules) >= 1


def test_rust_adapter_scans_throw_sites(rust_fixture: Path) -> None:
    adapter = RustAdapter()
    prod = adapter.find_production_files(rust_fixture)
    sites = adapter.scan_throw_sites(
        prod,
        hint_marker="Suggested fix:",
        domain_exception_types={"ValidationError"},
    )
    assert len(sites) >= 2
    # Should find custom ValidationError and generic panic!.
    assert any(s.exception_type == "ValidationError" for s in sites)
    assert any(s.is_generic for s in sites)
    assert any(s.is_user_defined for s in sites)
    assert any(s.has_fix_hint for s in sites)


def test_rust_adapter_scans_declarations(rust_fixture: Path) -> None:
    adapter = RustAdapter()
    prod = adapter.find_production_files(rust_fixture)
    declarations = adapter.scan_declarations(prod)
    names = {d.name for d in declarations}
    assert "SampleService" in names
    assert "ValidationError" in names
    assert "parse_config" in names
    # pub = public, no pub = private.
    svc_decl = next(d for d in declarations if d.name == "SampleService")
    assert svc_decl.visibility == "public"
    assert svc_decl.has_doc_comment is True
    private_names = {d.name for d in declarations if d.visibility == "private"}
    assert "internal_helper" in private_names


def test_rust_adapter_finds_test_methods(rust_fixture: Path) -> None:
    adapter = RustAdapter()
    # Rust inline tests are in prod files.
    prod = adapter.find_production_files(rust_fixture)
    methods = adapter.find_test_methods(prod)
    method_names = [name for _, name in methods]
    assert "test_do_work_positive_input_returns_double" in method_names
    assert len(methods) >= 2


def test_get_adapter_by_name_unknown_raises() -> None:
    with pytest.raises(NoAdapterError):
        get_adapter_by_name("cobol")
