"""E-012.3 legacy documentation integration and migration-planning tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ManifestError
from Engineering.ManifestSystem import (
    ManifestInspectionService,
    ManifestKind,
    ManifestMigrationPlanner,
    ManifestMigrationRegistry,
    ManifestMigrationService,
    ManifestMigrationStep,
    ManifestRecord,
    ManifestRegistry,
    ManifestSpec,
    SchemaCompatibility,
    default_manifest_migrations,
)


class _JsonAdapter:
    def __init__(self, spec: ManifestSpec) -> None:
        self.spec = spec

    def detect_schema_version(self, path: Path) -> int:
        value = json.loads(path.read_text(encoding="utf-8"))["schema_version"]
        assert isinstance(value, int)
        return value

    def validate(self, path: Path) -> int:
        return self.detect_schema_version(path)


def _write_documentation_manifest(
    path: Path,
    *,
    schema_version: int | None = None,
    document_path: str = "README.md",
    duplicate: bool = False,
) -> str:
    documents = [
        {"identifier": "readme", "path": document_path, "title": "Project"}
    ]
    if duplicate:
        documents.append(
            {"identifier": "readme", "path": "index.md", "title": "Index"}
        )
    payload: dict[str, object] = {
        "manifest": {
            "generated_by": "Engineering Toolkit",
            "output_root": "Engineering/Documentation/Generated",
            "documents": documents,
        }
    }
    if schema_version is not None:
        payload["schema_version"] = schema_version
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(content, encoding="utf-8")
    return content


class TestDocumentationManifestAdapter:
    def test_legacy_unversioned_yaml_is_backward_readable_schema_zero(
        self, tmp_path: Path
    ) -> None:
        _write_documentation_manifest(tmp_path / "documentation_manifest.yaml")

        report = ManifestInspectionService().inspect(tmp_path)

        assert report.passed
        assert len(report.records) == 1
        record = report.records[0]
        assert record.manifest_id == "ups.documentation"
        assert record.kind == ManifestKind.DOCUMENTATION
        assert record.schema_version == 0
        assert record.compatibility == SchemaCompatibility.READABLE

    def test_versioned_yaml_is_current_schema_one(self, tmp_path: Path) -> None:
        _write_documentation_manifest(
            tmp_path / "documentation_manifest.yaml", schema_version=1
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert report.passed
        assert report.records[0].schema_version == 1
        assert report.records[0].compatibility == SchemaCompatibility.CURRENT

    @pytest.mark.parametrize(
        "document_path, duplicate, message",
        (
            ("../README.md", False, "safe relative path"),
            ("docs\\README.md", False, "portable forward slashes"),
            ("README.md", True, "Duplicate documentation identifier"),
        ),
    )
    def test_rejects_unsafe_paths_and_duplicate_entries(
        self,
        tmp_path: Path,
        document_path: str,
        duplicate: bool,
        message: str,
    ) -> None:
        _write_documentation_manifest(
            tmp_path / "documentation_manifest.yaml",
            document_path=document_path,
            duplicate=duplicate,
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert not report.passed
        assert report.issues[0].code == "manifest.schema.invalid"
        assert message in report.issues[0].message

    def test_tracked_legacy_manifest_is_integrated_without_modification(self) -> None:
        generated_root = (
            Path(__file__).parents[2] / "Engineering" / "Documentation" / "Generated"
        )
        manifest_path = generated_root / "documentation_manifest.yaml"
        original = manifest_path.read_bytes()

        report = ManifestMigrationService().plan(generated_root)

        assert report.passed
        assert len(report.plans) == 1
        assert report.plans[0].source_version == 0
        assert manifest_path.read_bytes() == original


class TestManifestMigrationPlanning:
    def test_default_route_plans_documentation_zero_to_one(self, tmp_path: Path) -> None:
        original = _write_documentation_manifest(
            tmp_path / "documentation_manifest.yaml"
        )

        report = ManifestMigrationService().plan(tmp_path)

        assert report.passed
        assert len(report.plans) == 1
        plan = report.plans[0]
        assert (plan.manifest_id, plan.source_version, plan.target_version) == (
            "ups.documentation",
            0,
            1,
        )
        assert tuple(step.migration_id for step in plan.steps) == (
            "ups.documentation.v0-to-v1",
        )
        assert (tmp_path / "documentation_manifest.yaml").read_text(
            encoding="utf-8"
        ) == original
        assert report.summary == (
            "Manifest migration planning succeeded: 1 plan, 1 step, 0 issues."
        )

    def test_current_manifest_requires_no_plan(self, tmp_path: Path) -> None:
        _write_documentation_manifest(
            tmp_path / "documentation_manifest.yaml", schema_version=1
        )

        report = ManifestMigrationService().plan(tmp_path)

        assert report.passed
        assert report.plans == ()

    def test_registry_builds_shortest_deterministic_route(self) -> None:
        spec = ManifestSpec(
            "example.evolving",
            ManifestKind.BUILD,
            "evolving.json",
            (1, 2, 3),
            current_schema_version=3,
        )
        manifest_registry = ManifestRegistry((_JsonAdapter(spec),))
        steps = (
            ManifestMigrationStep("example.evolving", 2, 3, "v2-v3", "Step two."),
            ManifestMigrationStep("example.evolving", 1, 2, "v1-v2", "Step one."),
        )
        migration_registry = ManifestMigrationRegistry(manifest_registry, steps)

        route = migration_registry.route("example.evolving", 1, 3)

        assert route is not None
        assert tuple(step.migration_id for step in route) == ("v1-v2", "v2-v3")
        assert tuple(step.migration_id for step in migration_registry.steps) == (
            "v1-v2",
            "v2-v3",
        )

    def test_missing_route_is_reported_for_readable_manifest(self) -> None:
        spec = ManifestSpec(
            "example.evolving",
            ManifestKind.BUILD,
            "evolving.json",
            (1, 2),
            current_schema_version=2,
        )
        manifest_registry = ManifestRegistry((_JsonAdapter(spec),))
        planner = ManifestMigrationPlanner(
            manifest_registry,
            ManifestMigrationRegistry(manifest_registry),
        )
        record = ManifestRecord(
            "example.evolving",
            ManifestKind.BUILD,
            "evolving.json",
            1,
            "0" * 64,
            SchemaCompatibility.READABLE,
        )

        plans, issues = planner.plan((record,))

        assert plans == ()
        assert issues[0].code == "manifest.migration.unavailable"

    def test_registry_rejects_unsafe_and_duplicate_transitions(self) -> None:
        manifest_registry = ManifestInspectionService().registry
        registry = ManifestMigrationRegistry(
            manifest_registry, default_manifest_migrations()
        )
        duplicate = default_manifest_migrations()[0]

        with pytest.raises(ManifestError, match="Duplicate migration id"):
            registry.register(duplicate)
        with pytest.raises(ManifestError, match="forward-only"):
            registry.register(
                ManifestMigrationStep(
                    "ups.documentation", 1, 0, "backward", "Unsafe downgrade."
                )
            )
        with pytest.raises(ManifestError, match="Unknown manifest id"):
            registry.register(
                ManifestMigrationStep("missing", 0, 1, "missing", "Unknown family.")
            )

    def test_cli_prints_plan_and_step_without_writing(self, tmp_path: Path) -> None:
        _write_documentation_manifest(tmp_path / "documentation_manifest.yaml")

        result = CliRunner().invoke(
            app, ["manifest", "migrations", "--root", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert "PLAN ups.documentation schema=0->1" in result.output
        assert "STEP ups.documentation.v0-to-v1 schema=0->1" in result.output
        assert "Manifest migration planning succeeded" in result.output
