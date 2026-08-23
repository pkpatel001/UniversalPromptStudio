"""E-012.1 manifest registry, inspection, and CLI tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ManifestError
from Engineering.ManifestSystem import (
    ManifestInspectionService,
    ManifestKind,
    ManifestRegistry,
    ManifestSpec,
    default_manifest_adapters,
)


class _StubAdapter:
    def __init__(self, spec: ManifestSpec, schema_version: int = 1) -> None:
        self.spec = spec
        self.schema_version = schema_version

    def detect_schema_version(self, path: Path) -> int:
        assert path.is_file()
        return self.schema_version

    def validate(self, path: Path) -> int:
        assert path.is_file()
        return self.schema_version


def _write_json(path: Path, data: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


class TestManifestRegistry:
    def test_default_registry_is_stable_and_complete(self) -> None:
        registry = ManifestRegistry(default_manifest_adapters())

        assert tuple(adapter.spec.manifest_id for adapter in registry.adapters) == (
            "ups.ai-provider",
            "ups.build",
            "ups.documentation",
            "ups.plugin",
            "ups.release",
            "ups.template-artifact",
            "ups.theme",
        )
        assert registry.resolve_filename("build-manifest.json") is not None
        assert registry.resolve_filename("ai-provider-manifest.yaml") is not None
        assert registry.resolve_filename("documentation_manifest.yaml") is not None
        assert registry.resolve_filename("theme-manifest.yaml") is not None
        assert registry.resolve_filename("unrelated.json") is None

    def test_rejects_duplicate_ids_and_filenames(self) -> None:
        first = _StubAdapter(ManifestSpec("example.one", ManifestKind.BUILD, "one.json", (1,)))
        registry = ManifestRegistry((first,))

        with pytest.raises(ManifestError, match="Duplicate manifest id"):
            registry.register(
                _StubAdapter(
                    ManifestSpec("example.one", ManifestKind.RELEASE, "two.json", (1,))
                )
            )
        with pytest.raises(ManifestError, match="Duplicate manifest filename"):
            registry.register(
                _StubAdapter(
                    ManifestSpec("example.two", ManifestKind.RELEASE, "one.json", (1,))
                )
            )

    @pytest.mark.parametrize(
        "spec",
        (
            ManifestSpec("", ManifestKind.BUILD, "one.json", (1,)),
            ManifestSpec("example", ManifestKind.BUILD, "", (1,)),
            ManifestSpec("example", ManifestKind.BUILD, "one.json", ()),
            ManifestSpec("example", ManifestKind.BUILD, "one.json", (0,)),
        ),
    )
    def test_rejects_invalid_registration_metadata(self, spec: ManifestSpec) -> None:
        with pytest.raises(ManifestError):
            ManifestRegistry((_StubAdapter(spec),))

    def test_unknown_id_has_explicit_failure(self) -> None:
        with pytest.raises(ManifestError, match="Unknown manifest id"):
            ManifestRegistry().resolve_id("missing")


class TestManifestInspectionService:
    def test_discovers_valid_manifests_deterministically(self, tmp_path: Path) -> None:
        build_digest = _write_json(
            tmp_path / "build" / "build-manifest.json",
            {"schema_version": 1, "steps": []},
        )
        _write_json(
            tmp_path / "generated" / ".ups-artifact-manifest.json",
            {
                "schema_version": 1,
                "template": {"id": "project.basic", "version": "1.0.0"},
                "artifacts": [],
            },
        )
        _write_json(
            tmp_path / "release" / "release-manifest.json",
            {
                "schema_version": 1,
                "release": {"version": "0.2.0-alpha", "python_version": "0.2.0a0"},
                "artifacts": [],
            },
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert report.passed
        assert tuple(record.relative_path for record in report.records) == (
            "build/build-manifest.json",
            "generated/.ups-artifact-manifest.json",
            "release/release-manifest.json",
        )
        assert report.records[0].sha256 == build_digest
        assert all(len(record.sha256) == 64 for record in report.records)
        assert report.summary == "Manifest inspection succeeded: 3 valid, 0 invalid."

    def test_reports_invalid_manifest_without_stopping_scan(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "build-manifest.json",
            {"schema_version": 2, "steps": []},
        )
        _write_json(
            tmp_path / "release-manifest.json",
            {
                "schema_version": 1,
                "release": {"version": "0.2.0-alpha"},
                "artifacts": [],
            },
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert not report.passed
        assert tuple(record.manifest_id for record in report.records) == ("ups.release",)
        assert len(report.issues) == 1
        assert report.issues[0].relative_path == "build-manifest.json"
        assert report.issues[0].code == "manifest.schema.unsupported"

    def test_ignores_dependency_and_tool_cache_directories(self, tmp_path: Path) -> None:
        for directory in ("node_modules", "target", ".git", ".mypy_cache"):
            _write_json(
                tmp_path / directory / "build-manifest.json",
                {"schema_version": 2, "steps": []},
            )

        report = ManifestInspectionService().inspect(tmp_path)

        assert report.passed
        assert report.records == ()
        assert report.issues == ()

    def test_empty_tree_is_a_successful_inventory(self, tmp_path: Path) -> None:
        report = ManifestInspectionService().inspect(tmp_path)

        assert report.passed
        assert report.summary == "Manifest inspection succeeded: 0 valid, 0 invalid."

    def test_rejects_missing_inspection_root(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError, match="not a directory"):
            ManifestInspectionService().inspect(tmp_path / "missing")


class TestManifestCli:
    def test_lists_registered_types(self) -> None:
        result = CliRunner().invoke(app, ["manifest", "types"])

        assert result.exit_code == 0
        assert "ups.build: build-manifest.json (current: 1; readable: 1" in result.output
        assert "ups.ai-provider: ai-provider-manifest.yaml" in result.output
        assert "ups.documentation: documentation_manifest.yaml" in result.output
        assert "current: 1; readable: 0, 1" in result.output
        assert "ups.release: release-manifest.json (current: 1; readable: 1" in result.output
        assert "ups.template-artifact: .ups-artifact-manifest.json" in result.output
        assert "cardinality: many" in result.output

    def test_inspects_explicit_root(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "build-manifest.json",
            {"schema_version": 1, "steps": []},
        )

        result = CliRunner().invoke(app, ["manifest", "inspect", "--root", str(tmp_path)])

        assert result.exit_code == 0
        assert "VALID ups.build schema=1 path=build-manifest.json" in result.output
        assert "Manifest inspection succeeded: 1 valid, 0 invalid." in result.output

    def test_invalid_manifest_returns_validation_failure(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "release-manifest.json",
            {"schema_version": 99, "release": {}, "artifacts": []},
        )

        result = CliRunner().invoke(app, ["manifest", "inspect", "--root", str(tmp_path)])

        assert result.exit_code != 0
        assert "FAILED manifest.schema.unsupported" in result.output
        assert "Manifest inspection failed: 0 valid, 1 invalid." in result.output
