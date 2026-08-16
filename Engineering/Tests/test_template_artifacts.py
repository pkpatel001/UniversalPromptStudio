"""E-009 template and artifact system tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from Engineering.CodeGeneration import (
    ArtifactInfo,
    DirectoryTemplateRepository,
    GenerationContext,
    GenerationEngine,
    GeneratorInfo,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import (
    CodeGenerationError,
    GenerationValidationError,
    TemplateError,
)
from Engineering.Templates import (
    ArtifactDefinition,
    ArtifactManifestBuilder,
    DirectoryTemplateDefinitionRepository,
    TemplateArtifactService,
    TemplateCatalog,
    TemplateCategory,
    TemplateDefinition,
    TemplateDefinitionValidator,
    TemplateMetadata,
    TemplateVariable,
    VariableKind,
    built_in_definition_repository,
)


def _definition(version: str = "1.0.0") -> TemplateDefinition:
    return TemplateDefinition(
        metadata=TemplateMetadata(
            template_id="python.component",
            name="Python component",
            version=version,
            category=TemplateCategory.PYTHON,
        ),
        variables=(
            TemplateVariable("class_name"),
            TemplateVariable(
                "description",
                kind=VariableKind.DEFAULTED,
                default="Generated component",
            ),
            TemplateVariable("notes", kind=VariableKind.OPTIONAL),
        ),
        artifacts=(
            ArtifactDefinition(
                relative_path="component.py",
                source_template_id="python.component",
                name="component",
            ),
        ),
    )


def _context() -> GenerationContext:
    return GenerationContext(
        project=ProjectGenerationInfo("Project", "P", "1.0.0", "Company", "MPL-2.0"),
        generator=GeneratorInfo("python.component"),
        artifact=ArtifactInfo("component"),
    )


class TestTemplateCatalog:
    def test_register_resolve_and_list_deterministically(self) -> None:
        catalog = TemplateCatalog()
        catalog.register(_definition("1.0.0"))
        catalog.register(_definition("1.10.0"))
        catalog.register(_definition("1.2.0"))

        assert catalog.resolve("python.component").version == "1.10.0"
        assert len(catalog.definitions(TemplateCategory.PYTHON)) == 3

    def test_exact_version_and_contains(self) -> None:
        catalog = TemplateCatalog()
        definition = _definition()
        catalog.register(definition)

        assert catalog.contains("python.component", "1.0.0")
        assert catalog.resolve("python.component", "1.0.0") is definition

    def test_duplicate_and_unknown_are_rejected(self) -> None:
        catalog = TemplateCatalog()
        catalog.register(_definition())

        with pytest.raises(CodeGenerationError, match="already registered"):
            catalog.register(_definition())
        with pytest.raises(CodeGenerationError, match="No template definition"):
            catalog.resolve("missing.template")


class TestTemplateDefinitionValidation:
    def test_valid_definition_has_no_issues(self, tmp_path: Path) -> None:
        source = tmp_path / "python"
        source.mkdir()
        (source / "component.j2").write_text(
            "class {{ values.class_name }}:\n    pass\n",
            encoding="utf-8",
        )
        repository = DirectoryTemplateRepository(tmp_path)

        issues = TemplateDefinitionValidator(repository).validate(_definition())

        assert issues == ()

    def test_reports_invalid_structure_and_unknown_source(self, tmp_path: Path) -> None:
        definition = TemplateDefinition(
            metadata=TemplateMetadata(
                template_id="INVALID",
                name="",
                version="one",
                category=TemplateCategory.PYTHON,
            ),
            variables=(
                TemplateVariable("Bad Name"),
                TemplateVariable("same"),
                TemplateVariable("same"),
            ),
            artifacts=(ArtifactDefinition("../bad.py", "missing.source"),),
        )

        issues = TemplateDefinitionValidator(
            DirectoryTemplateRepository(tmp_path)
        ).validate(definition)
        rule_ids = {issue.rule_id for issue in issues}

        assert "template.invalid-id" in rule_ids
        assert "template.invalid-version" in rule_ids
        assert "template.duplicate-variable" in rule_ids
        assert "template.invalid-artifact-path" in rule_ids
        assert "template.unknown-source" in rule_ids


class TestTemplateArtifactService:
    def test_builds_request_with_defaults_and_artifact_values(self) -> None:
        request = TemplateArtifactService().build_request(
            _definition(),
            destination="generated",
            context=_context(),
            values={"class_name": "Example"},
            dry_run=True,
        )

        assert request.generator_id == "python.component"
        assert request.dry_run is True
        assert request.artifacts[0].values["class_name"] == "Example"
        assert request.artifacts[0].values["description"] == "Generated component"
        assert "notes" not in request.artifacts[0].values

    def test_missing_and_unknown_variables_are_rejected(self) -> None:
        service = TemplateArtifactService()
        with pytest.raises(GenerationValidationError, match="Missing required"):
            service.build_request(_definition(), destination="out", context=_context())
        with pytest.raises(GenerationValidationError, match="Unknown template"):
            service.build_request(
                _definition(),
                destination="out",
                context=_context(),
                values={"class_name": "Example", "surprise": True},
            )

    def test_invalid_variable_type_is_rejected(self) -> None:
        with pytest.raises(GenerationValidationError, match="expected string"):
            TemplateArtifactService().build_request(
                _definition(),
                destination="out",
                context=_context(),
                values={"class_name": 42},
            )

    def test_definition_runs_through_e008_engine(self, tmp_path: Path) -> None:
        source = tmp_path / "templates" / "python"
        source.mkdir(parents=True)
        (source / "component.j2").write_text(
            '"""{{ values.description }}"""\n\nclass {{ values.class_name }}:\n    pass\n',
            encoding="utf-8",
        )
        repository = DirectoryTemplateRepository(tmp_path / "templates")
        validator = TemplateDefinitionValidator(repository)
        request = TemplateArtifactService(validator).build_request(
            _definition(),
            destination="generated",
            context=_context(),
            values={"class_name": "Example"},
        )

        report = GenerationEngine(repository, tmp_path).generate(request)

        assert report.success
        assert report.generated_count == 1
        output = (tmp_path / "generated" / "component.py").read_text(encoding="utf-8")
        assert "class Example" in output
        assert "Generated component" in output


class TestTemplateDefinitionDiscovery:
    def test_built_in_definition_is_valid(self) -> None:
        repository = built_in_definition_repository()

        definition = repository.resolve("project.basic")

        assert definition.metadata.category == TemplateCategory.PROJECT
        assert len(definition.artifacts) == 3

    def test_cli_lists_built_in_definitions(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        result = CliRunner().invoke(app, ["generate", "templates"])

        assert result.exit_code == 0
        assert "project.basic" in result.output
        assert "Basic project artifacts" in result.output

    def test_cli_inspects_and_validates_built_in_definitions(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        inspect_result = runner.invoke(
            app, ["generate", "templates", "inspect", "project.basic"]
        )
        validate_result = runner.invoke(
            app, ["generate", "templates", "validate"]
        )

        assert inspect_result.exit_code == 0
        assert "README.md <- markdown.readme" in inspect_result.output
        assert validate_result.exit_code == 0
        assert "Validated 1 template definition" in validate_result.output

    def test_discovers_and_resolves_yaml_definitions(self, tmp_path: Path) -> None:
        source = tmp_path / "sources" / "python"
        source.mkdir(parents=True)
        (source / "component.j2").write_text(
            "class {{ values.class_name }}:\n    pass\n", encoding="utf-8"
        )
        definitions = tmp_path / "definitions" / "python"
        definitions.mkdir(parents=True)
        (definitions / "component.template.yaml").write_text(
            """metadata:
  id: python.component
  name: Python component
  version: 1.0.0
  category: python
  tags: [python, component]
variables:
  - name: class_name
    kind: required
    type: string
artifacts:
  - path: component.py
    template: python.component
    type: source
""",
            encoding="utf-8",
        )
        validator = TemplateDefinitionValidator(
            DirectoryTemplateRepository(tmp_path / "sources")
        )
        repository = DirectoryTemplateDefinitionRepository(
            tmp_path / "definitions", validator
        )

        definition = repository.resolve("python.component")

        assert repository.definition_ids() == ("python.component",)
        assert definition.version == "1.0.0"
        assert definition.metadata.tags == ("python", "component")
        assert definition.variables[0].kind == VariableKind.REQUIRED

    def test_invalid_definition_is_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "bad.template.yaml").write_text(
            "metadata: invalid\n", encoding="utf-8"
        )

        with pytest.raises(TemplateError, match="Invalid template definition"):
            DirectoryTemplateDefinitionRepository(tmp_path).definitions()

    def test_empty_or_missing_root_is_deterministic(self, tmp_path: Path) -> None:
        repository = DirectoryTemplateDefinitionRepository(tmp_path / "missing")

        assert repository.definitions() == ()
        assert repository.definition_ids() == ()


class TestArtifactManifest:
    def test_builds_sorted_manifest_with_content_hashes(self, tmp_path: Path) -> None:
        source = tmp_path / "templates" / "python"
        source.mkdir(parents=True)
        (source / "component.j2").write_text(
            "class {{ values.class_name }}:\n    pass\n", encoding="utf-8"
        )
        repository = DirectoryTemplateRepository(tmp_path / "templates")
        validator = TemplateDefinitionValidator(repository)
        definition = _definition()
        request = TemplateArtifactService(validator).build_request(
            definition,
            destination="generated",
            context=_context(),
            values={"class_name": "Example"},
        )
        report = GenerationEngine(repository, tmp_path).generate(request)

        manifest = ArtifactManifestBuilder().build(
            definition, report, tmp_path / "generated"
        )
        manifest_path = tmp_path / "manifest.json"
        manifest.write(manifest_path)

        assert manifest.template_id == "python.component"
        assert manifest.artifacts[0].sha256
        first = manifest_path.read_text(encoding="utf-8")
        manifest.write(manifest_path)
        assert manifest_path.read_text(encoding="utf-8") == first
        assert '"schema_version": 1' in first

        loaded = type(manifest).read(manifest_path)
        assert loaded == manifest
        assert loaded.verify(tmp_path / "generated").passed

        (tmp_path / "generated" / "component.py").write_text(
            "tampered", encoding="utf-8"
        )
        verification = loaded.verify(tmp_path / "generated")
        assert verification.passed is False
        assert verification.issues[0].relative_path == "component.py"
