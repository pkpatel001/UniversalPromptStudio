"""E-012.2 schema compatibility and cross-manifest relationship tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ManifestError
from Engineering.ManifestSystem import (
    ManifestDependency,
    ManifestInspectionService,
    ManifestKind,
    ManifestRecord,
    ManifestRegistry,
    ManifestRelationshipValidator,
    ManifestSchemaContract,
    ManifestSpec,
    ManifestValidationService,
    SchemaCompatibility,
    default_manifest_adapters,
    default_manifest_dependencies,
)


class _EchoSchemaAdapter:
    def __init__(self, spec: ManifestSpec) -> None:
        self.spec = spec

    def validate(self, path: Path) -> int:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = data["schema_version"]
        assert isinstance(value, int)
        return value


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _record(manifest_id: str, path: str) -> ManifestRecord:
    kind = {
        "ups.build": ManifestKind.BUILD,
        "ups.release": ManifestKind.RELEASE,
        "ups.template-artifact": ManifestKind.TEMPLATE_ARTIFACT,
    }[manifest_id]
    return ManifestRecord(manifest_id, kind, path, 1, "0" * 64)


class TestManifestSchemaContracts:
    def test_classifies_current_readable_and_unsupported_versions(self) -> None:
        contract = ManifestSchemaContract(current_version=2, readable_versions=(1, 2))

        assert contract.compatibility(2) == SchemaCompatibility.CURRENT
        assert contract.compatibility(1) == SchemaCompatibility.READABLE
        assert contract.compatibility(3) == SchemaCompatibility.UNSUPPORTED
        assert contract.compatibility(True) == SchemaCompatibility.UNSUPPORTED

    @pytest.mark.parametrize(
        "spec, message",
        (
            (
                ManifestSpec("example", ManifestKind.BUILD, "example.json", (2, 1)),
                "unique and ascending",
            ),
            (
                ManifestSpec("example", ManifestKind.BUILD, "example.json", (1, 1)),
                "unique and ascending",
            ),
            (
                ManifestSpec(
                    "example",
                    ManifestKind.BUILD,
                    "example.json",
                    (1, 2),
                    current_schema_version=1,
                ),
                "latest readable",
            ),
            (
                ManifestSpec(
                    "example",
                    ManifestKind.BUILD,
                    "example.json",
                    (1,),
                    current_schema_version=True,
                ),
                "must be an integer",
            ),
        ),
    )
    def test_registry_rejects_ambiguous_evolution_contracts(
        self, spec: ManifestSpec, message: str
    ) -> None:
        with pytest.raises(ManifestError, match=message):
            ManifestRegistry((_EchoSchemaAdapter(spec),))

    def test_inspection_records_backward_readable_version(self, tmp_path: Path) -> None:
        spec = ManifestSpec(
            "example.evolving",
            ManifestKind.BUILD,
            "evolving.json",
            (1, 2),
            current_schema_version=2,
        )
        registry = ManifestRegistry((_EchoSchemaAdapter(spec),))
        _write_json(tmp_path / "evolving.json", {"schema_version": 1})

        report = ManifestInspectionService(registry).inspect(tmp_path)

        assert report.passed
        assert report.records[0].compatibility == SchemaCompatibility.READABLE

    def test_inspection_reports_unsupported_version_explicitly(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "build-manifest.json",
            {"schema_version": 2, "steps": []},
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert not report.passed
        assert report.issues[0].code == "manifest.schema.unsupported"

    def test_inspection_rejects_adapter_schema_disagreement(self, tmp_path: Path) -> None:
        class _MismatchedAdapter(_EchoSchemaAdapter):
            def validate(self, path: Path) -> int:
                super().validate(path)
                return 2

        spec = ManifestSpec("example", ManifestKind.BUILD, "example.json", (1,))
        registry = ManifestRegistry((_MismatchedAdapter(spec),))
        _write_json(tmp_path / "example.json", {"schema_version": 1})

        report = ManifestInspectionService(registry).inspect(tmp_path)

        assert not report.passed
        assert report.issues[0].code == "manifest.schema.invalid"
        assert "returned schema version 2, expected 1" in report.issues[0].message

    @pytest.mark.parametrize("schema_version", (True, "1", None))
    def test_inspection_rejects_non_integer_schema_version(
        self, tmp_path: Path, schema_version: object
    ) -> None:
        _write_json(
            tmp_path / "build-manifest.json",
            {"schema_version": schema_version, "steps": []},
        )

        report = ManifestInspectionService().inspect(tmp_path)

        assert report.issues[0].code == "manifest.schema.invalid"


class TestManifestRelationships:
    def setup_method(self) -> None:
        self.registry = ManifestRegistry(default_manifest_adapters())
        self.validator = ManifestRelationshipValidator(
            self.registry, default_manifest_dependencies()
        )

    def test_release_requires_build_manifest(self) -> None:
        issues = self.validator.validate((_record("ups.release", "release/manifest.json"),))

        assert len(issues) == 1
        assert issues[0].code == "manifest.relationship.missing"
        assert "ups.release requires ups.build" in issues[0].message

    def test_release_and_build_form_valid_graph(self) -> None:
        issues = self.validator.validate(
            (
                _record("ups.release", "release/release-manifest.json"),
                _record("ups.build", "build/build-manifest.json"),
            )
        )

        assert issues == ()

    def test_singleton_family_rejects_duplicate_documents(self) -> None:
        issues = self.validator.validate(
            (
                _record("ups.build", "a/build-manifest.json"),
                _record("ups.build", "b/build-manifest.json"),
            )
        )

        assert len(issues) == 1
        assert issues[0].relative_path == "b/build-manifest.json"
        assert issues[0].code == "manifest.cardinality"

    def test_template_artifact_family_allows_multiple_documents(self) -> None:
        issues = self.validator.validate(
            (
                _record("ups.template-artifact", "a/.ups-artifact-manifest.json"),
                _record("ups.template-artifact", "b/.ups-artifact-manifest.json"),
            )
        )

        assert issues == ()

    def test_rejects_unknown_self_duplicate_and_cyclic_dependencies(self) -> None:
        with pytest.raises(ManifestError, match="Unknown manifest id"):
            ManifestRelationshipValidator(
                self.registry, (ManifestDependency("missing", "ups.build"),)
            )
        with pytest.raises(ManifestError, match="cannot reference themselves"):
            ManifestRelationshipValidator(
                self.registry, (ManifestDependency("ups.build", "ups.build"),)
            )
        duplicate = ManifestDependency("ups.release", "ups.build")
        with pytest.raises(ManifestError, match="Duplicate manifest dependency"):
            ManifestRelationshipValidator(self.registry, (duplicate, duplicate))
        with pytest.raises(ManifestError, match="Cyclic manifest dependency"):
            ManifestRelationshipValidator(
                self.registry,
                (
                    ManifestDependency("ups.release", "ups.build"),
                    ManifestDependency("ups.build", "ups.release"),
                ),
            )


class TestManifestValidationService:
    def test_combines_inspection_and_relationship_validation(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "release" / "release-manifest.json",
            {
                "schema_version": 1,
                "release": {"version": "0.2.0-alpha"},
                "artifacts": [],
            },
        )

        missing = ManifestValidationService().validate(tmp_path)

        assert not missing.passed
        assert missing.issues[0].code == "manifest.relationship.missing"

        _write_json(
            tmp_path / "build" / "build-manifest.json",
            {"schema_version": 1, "steps": []},
        )
        complete = ManifestValidationService().validate(tmp_path)

        assert complete.passed
        assert complete.summary == "Manifest validation succeeded: 2 valid, 0 issues."

    def test_structural_failure_does_not_cascade_relationship_errors(
        self, tmp_path: Path
    ) -> None:
        _write_json(
            tmp_path / "release-manifest.json",
            {"schema_version": 99, "release": {}, "artifacts": []},
        )

        report = ManifestValidationService().validate(tmp_path)

        assert len(report.issues) == 1
        assert report.issues[0].code == "manifest.schema.unsupported"

    def test_cli_validates_complete_manifest_graph(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "build-manifest.json",
            {"schema_version": 1, "steps": []},
        )
        _write_json(
            tmp_path / "release-manifest.json",
            {
                "schema_version": 1,
                "release": {"version": "0.2.0-alpha"},
                "artifacts": [],
            },
        )

        result = CliRunner().invoke(app, ["manifest", "validate", "--root", str(tmp_path)])

        assert result.exit_code == 0
        assert "compatibility=current" in result.output
        assert "Manifest validation succeeded: 2 valid, 0 issues." in result.output
