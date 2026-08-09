"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Code Generation Framework Tests

Tests cover:
- Domain models (creation, immutability, properties)
- Template resolution (valid, missing, invalid, deterministic)
- Template rendering (substitution, missing vars, malformed, deterministic)
- Planning (validation, duplicates, empty requests)
- Safety policies (path traversal, boundary, protected, secrets)
- Conflict policy (create, unchanged, conflict)
- Generation engine (full pipeline, multi-artifact, dry-run, partial failure)
- Generator registry (register, resolve, duplicate)
- Determinism (byte-identical output)
- CLI integration

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Engineering.CodeGeneration.engine import GenerationEngine
from Engineering.CodeGeneration.generator import Generator, StaticGenerator
from Engineering.CodeGeneration.models import (
    ArtifactInfo,
    ArtifactResult,
    ArtifactSpec,
    ArtifactState,
    GeneratedArtifact,
    GenerationContext,
    GenerationPlan,
    GenerationReport,
    GenerationRequest,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
    project_context_from_config,
)
from Engineering.CodeGeneration.planner import GenerationPlanner
from Engineering.CodeGeneration.policies import validate_destination, validate_no_secrets
from Engineering.CodeGeneration.registry import GeneratorRegistry
from Engineering.CodeGeneration.renderer import TemplateRenderer
from Engineering.CodeGeneration.templates import (
    DirectoryTemplateRepository,
    Template,
    auto_generated_header,
)
from Engineering.core.exceptions import (
    CodeGenerationError,
    GenerationValidationError,
    SecretContextError,
    TemplateNotFoundError,
    TemplateRenderError,
    UnsafeDestinationError,
)
from Engineering.core.validation import ValidationIssue, ValidationSeverity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project_info() -> ProjectGenerationInfo:
    return ProjectGenerationInfo(
        name="Test Project",
        short_name="TP",
        version="1.0.0",
        company="Test Corp",
        license="MIT",
    )


def _make_generator_info() -> GeneratorInfo:
    return GeneratorInfo(generator_id="test-gen", name="Test Generator", version="0.1.0")


def _make_artifact_info(name: str = "module") -> ArtifactInfo:
    return ArtifactInfo(name=name, description=f"A {name} artifact")


def _make_context(**values: object) -> GenerationContext:
    return GenerationContext(
        project=_make_project_info(),
        generator=_make_generator_info(),
        artifact=_make_artifact_info(),
        values=values,
    )


def _make_request(
    artifacts: tuple[ArtifactSpec, ...] | None = None,
    destination: str = "output",
    overwrite: OverwritePolicy = OverwritePolicy.NEVER,
    dry_run: bool = False,
    generator_id: str = "test-gen",
    **values: object,
) -> GenerationRequest:
    if artifacts is None:
        artifacts = (
            ArtifactSpec(
                relative_path="hello.py",
                template_id="python.module",
                name="hello",
            ),
        )
    return GenerationRequest(
        generator_id=generator_id,
        destination=destination,
        context=_make_context(**values),
        artifacts=artifacts,
        overwrite=overwrite,
        dry_run=dry_run,
    )


def _create_template_dir(tmp_path: Path) -> Path:
    """Create a template directory with sample templates."""
    templates_root = tmp_path / "templates"
    python_dir = templates_root / "python"
    python_dir.mkdir(parents=True)
    (python_dir / "module.j2").write_text(
        "# {{ project.name }}\nversion = '{{ project.version }}'\n",
        encoding="utf-8",
    )
    (python_dir / "package.j2").write_text(
        '"""{{ artifact.description }}"""\n',
        encoding="utf-8",
    )
    yaml_dir = templates_root / "yaml"
    yaml_dir.mkdir()
    (yaml_dir / "config.j2").write_text(
        "# {{ project.name }}\n{{ artifact.name }}:\n  version: '{{ project.version }}'\n",
        encoding="utf-8",
    )
    return templates_root


def _create_fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake project with template and output dirs."""
    templates_root = _create_template_dir(tmp_path)
    (tmp_path / "output").mkdir()
    return templates_root


# =============================================================================
# Domain Models
# =============================================================================


class TestArtifactState:
    def test_values(self) -> None:
        assert ArtifactState.CREATED.value == "created"
        assert ArtifactState.UNCHANGED.value == "unchanged"
        assert ArtifactState.OVERWRITTEN.value == "overwritten"
        assert ArtifactState.SKIPPED.value == "skipped"
        assert ArtifactState.CONFLICT.value == "conflict"
        assert ArtifactState.FAILED.value == "failed"

    def test_all_states_unique(self) -> None:
        values = [s.value for s in ArtifactState]
        assert len(values) == len(set(values))


class TestOverwritePolicy:
    def test_values(self) -> None:
        assert OverwritePolicy.NEVER.value == "never"
        assert OverwritePolicy.ALLOWED.value == "allowed"


class TestProjectGenerationInfo:
    def test_creation(self) -> None:
        info = _make_project_info()
        assert info.name == "Test Project"
        assert info.version == "1.0.0"

    def test_immutable(self) -> None:
        info = _make_project_info()
        with pytest.raises(AttributeError):
            info.name = "Changed"  # type: ignore[misc]


class TestGeneratorInfo:
    def test_creation(self) -> None:
        info = _make_generator_info()
        assert info.generator_id == "test-gen"
        assert info.name == "Test Generator"

    def test_immutable(self) -> None:
        info = _make_generator_info()
        with pytest.raises(AttributeError):
            info.generator_id = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        info = GeneratorInfo(generator_id="x")
        assert info.name == ""
        assert info.version == ""


class TestArtifactInfo:
    def test_creation(self) -> None:
        info = ArtifactInfo(name="test", description="A test")
        assert info.name == "test"
        assert info.description == "A test"

    def test_immutable(self) -> None:
        info = ArtifactInfo(name="test")
        with pytest.raises(AttributeError):
            info.name = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        info = ArtifactInfo(name="test")
        assert info.description == ""


class TestGenerationContext:
    def test_creation(self) -> None:
        ctx = _make_context(foo="bar")
        assert ctx.project.name == "Test Project"
        assert ctx.values["foo"] == "bar"

    def test_immutable(self) -> None:
        ctx = _make_context()
        with pytest.raises(AttributeError):
            ctx.project = None  # type: ignore[assignment]

    def test_default_values(self) -> None:
        ctx = GenerationContext(
            project=_make_project_info(),
            generator=_make_generator_info(),
            artifact=_make_artifact_info(),
        )
        assert ctx.values == {}


class TestProjectContextFromConfig:
    def test_builds_from_config(self, tmp_path: Path) -> None:
        from Engineering.core.config import (
            CacheConfiguration,
            Configuration,
            DocumentationConfiguration,
            DocumentationGenerateConfiguration,
            DocumentationOutputConfiguration,
            EngineeringConfiguration,
            EngineeringPathsConfiguration,
            LoggingConfiguration,
            ProjectConfiguration,
            PythonConfiguration,
            ValidationConfiguration,
        )

        config = Configuration(
            project=ProjectConfiguration(
                name="P",
                short_name="PS",
                company="C",
                version="0.1.0",
                license="MIT",
                python=PythonConfiguration(minimum_version="3.12"),
            ),
            engineering=EngineeringConfiguration(
                strict_mode=True,
                diagnostics=True,
                cache=CacheConfiguration(enabled=True),
                validation=ValidationConfiguration(enabled=True),
                paths=EngineeringPathsConfiguration(verify_on_startup=True),
            ),
            documentation=DocumentationConfiguration(
                enabled=True,
                output=DocumentationOutputConfiguration(root="docs"),
                generate=DocumentationGenerateConfiguration(
                    readme=True, api=False, architecture=False,
                    adrs=False, project_status=False,
                    changelog=False, index=False, manifests=False,
                ),
            ),
            logging=LoggingConfiguration(
                enabled=True, level="INFO",
                console=True, file=False,
                directory="logs", filename="eng.log",
            ),
        )

        info = project_context_from_config(config)
        assert info.name == "P"
        assert info.short_name == "PS"
        assert info.version == "0.1.0"
        assert info.company == "C"
        assert info.license == "MIT"


class TestArtifactSpec:
    def test_creation(self) -> None:
        spec = ArtifactSpec(relative_path="test.py", template_id="python.module")
        assert spec.relative_path == "test.py"
        assert spec.template_id == "python.module"

    def test_defaults(self) -> None:
        spec = ArtifactSpec(relative_path="x.py", template_id="t")
        assert spec.artifact_type == "source"
        assert spec.name == ""
        assert spec.values == {}

    def test_immutable(self) -> None:
        spec = ArtifactSpec(relative_path="x.py", template_id="t")
        with pytest.raises(AttributeError):
            spec.relative_path = "y.py"  # type: ignore[misc]


class TestGenerationPlan:
    def test_is_valid_no_issues(self) -> None:
        plan = GenerationPlan(
            generator_id="g",
            destination_root=Path("/out"),
            artifacts=(ArtifactSpec(relative_path="x.py", template_id="t"),),
        )
        assert plan.is_valid is True

    def test_is_valid_with_error(self) -> None:
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule_id="test",
            message="error",
        )
        plan = GenerationPlan(
            generator_id="g",
            destination_root=Path("/out"),
            issues=(issue,),
        )
        assert plan.is_valid is False

    def test_is_valid_with_warning_only(self) -> None:
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            rule_id="test",
            message="warning",
        )
        plan = GenerationPlan(
            generator_id="g",
            destination_root=Path("/out"),
            issues=(issue,),
        )
        assert plan.is_valid is True

    def test_immutable(self) -> None:
        plan = GenerationPlan(generator_id="g", destination_root=Path("/out"))
        with pytest.raises(AttributeError):
            plan.generator_id = "x"  # type: ignore[misc]


class TestGeneratedArtifact:
    def test_creation(self) -> None:
        artifact = GeneratedArtifact(
            relative_path="x.py",
            content="hello",
            artifact_type="source",
            source_template="python.module",
        )
        assert artifact.content == "hello"

    def test_immutable(self) -> None:
        artifact = GeneratedArtifact(
            relative_path="x.py", content="c",
            artifact_type="s", source_template="t",
        )
        with pytest.raises(AttributeError):
            artifact.content = "changed"  # type: ignore[misc]


class TestArtifactResult:
    def test_creation(self) -> None:
        result = ArtifactResult(
            state=ArtifactState.CREATED,
            relative_path="x.py",
        )
        assert result.state == ArtifactState.CREATED
        assert result.reason == ""

    def test_immutable(self) -> None:
        result = ArtifactResult(state=ArtifactState.CREATED, relative_path="x.py")
        with pytest.raises(AttributeError):
            result.state = ArtifactState.FAILED  # type: ignore[misc]


class TestGenerationRequest:
    def test_creation(self) -> None:
        request = _make_request()
        assert request.generator_id == "test-gen"
        assert request.overwrite == OverwritePolicy.NEVER
        assert request.dry_run is False

    def test_immutable(self) -> None:
        request = _make_request()
        with pytest.raises(AttributeError):
            request.generator_id = "x"  # type: ignore[misc]


class TestGenerationReport:
    def test_empty_report(self) -> None:
        report = GenerationReport()
        assert report.success is True
        assert report.summary != ""

    def test_success_all_created(self) -> None:
        report = GenerationReport(
            results=(
                ArtifactResult(state=ArtifactState.CREATED, relative_path="a.py"),
                ArtifactResult(state=ArtifactState.CREATED, relative_path="b.py"),
            ),
        )
        assert report.success is True
        assert report.generated_count == 2
        assert report.conflict_count == 0

    def test_conflict_report(self) -> None:
        report = GenerationReport(
            results=(
                ArtifactResult(state=ArtifactState.CONFLICT, relative_path="a.py"),
            ),
        )
        assert report.success is False
        assert report.conflict_count == 1

    def test_failure_report(self) -> None:
        report = GenerationReport(
            results=(
                ArtifactResult(
                    state=ArtifactState.FAILED,
                    relative_path="a.py",
                    reason="error",
                ),
            ),
        )
        assert report.success is False
        assert report.failed_count == 1

    def test_mixed_results(self) -> None:
        report = GenerationReport(
            results=(
                ArtifactResult(state=ArtifactState.CREATED, relative_path="a.py"),
                ArtifactResult(state=ArtifactState.UNCHANGED, relative_path="b.py"),
                ArtifactResult(state=ArtifactState.SKIPPED, relative_path="c.py"),
                ArtifactResult(state=ArtifactState.OVERWRITTEN, relative_path="d.py"),
                ArtifactResult(state=ArtifactState.CONFLICT, relative_path="e.py"),
                ArtifactResult(
                    state=ArtifactState.FAILED,
                    relative_path="f.py",
                    reason="err",
                ),
            ),
        )
        assert report.generated_count == 2
        assert report.unchanged_count == 1
        assert report.skipped_count == 1
        assert report.overwritten_count == 1
        assert report.conflict_count == 1
        assert report.failed_count == 1

    def test_dry_run_summary(self) -> None:
        report = GenerationReport(
            results=(
                ArtifactResult(state=ArtifactState.CREATED, relative_path="a.py"),
            ),
            dry_run=True,
        )
        assert "Dry-run" in report.summary

    def test_immutable(self) -> None:
        report = GenerationReport()
        with pytest.raises(AttributeError):
            report.results = ()  # type: ignore[misc]


# =============================================================================
# Templates
# =============================================================================


class TestTemplate:
    def test_creation(self) -> None:
        t = Template(template_id="python.module", name="module", source="x")
        assert t.template_id == "python.module"

    def test_immutable(self) -> None:
        t = Template(template_id="x", name="x", source="x")
        with pytest.raises(AttributeError):
            t.template_id = "y"  # type: ignore[misc]


class TestDirectoryTemplateRepository:
    def test_resolve_existing(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        template = repo.resolve("python.module")
        assert template.template_id == "python.module"
        assert template.language == "python"
        assert template.name == "module"
        assert "version" in template.source

    def test_resolve_missing(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        with pytest.raises(TemplateNotFoundError, match="Template not found"):
            repo.resolve("python.nonexistent")

    def test_resolve_invalid_id(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        with pytest.raises(TemplateNotFoundError, match="Invalid template identifier"):
            repo.resolve("Invalid-ID!!!")

    def test_resolve_single_component(self, tmp_path: Path) -> None:
        root = tmp_path / "templates"
        (root / "standalone.j2").mkdir(parents=True)
        repo = DirectoryTemplateRepository(root)
        with pytest.raises(TemplateNotFoundError, match="Invalid template identifier"):
            repo.resolve("standalone")

    def test_contains(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        assert repo.contains("python.module") is True
        assert repo.contains("python.nonexistent") is False

    def test_template_ids(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        ids = repo.template_ids()
        assert "python.module" in ids
        assert "python.package" in ids

    def test_deterministic_resolution(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        t1 = repo.resolve("python.module")
        t2 = repo.resolve("python.module")
        assert t1.source == t2.source
        assert t1.template_id == t2.template_id

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        with pytest.raises(TemplateNotFoundError, match="Invalid template identifier"):
            repo.resolve("python.../../../etc/passwd")

    def test_root_property(self, tmp_path: Path) -> None:
        root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(root)
        assert repo.root == root.resolve()

    def test_empty_repository(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        repo = DirectoryTemplateRepository(empty)
        assert repo.template_ids() == ()


# =============================================================================
# Renderer
# =============================================================================


class TestTemplateRenderer:
    def test_render_basic(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        result = renderer.render("Hello {{ project.name }}", ctx)
        assert result == "Hello Test Project"

    def test_render_with_values(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context(foo="bar")
        result = renderer.render("{{ values.foo }}", ctx)
        assert result == "bar"

    def test_render_missing_variable(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        with pytest.raises(TemplateRenderError):
            renderer.render("{{ values.nonexistent }}", ctx)

    def test_render_malformed_template(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        with pytest.raises(TemplateRenderError, match="syntax error"):
            renderer.render("{% if %}", ctx)

    def test_render_deterministic(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        r1 = renderer.render("Hello {{ project.name }}", ctx)
        r2 = renderer.render("Hello {{ project.name }}", ctx)
        assert r1 == r2

    def test_render_empty_template(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        result = renderer.render("", ctx)
        assert result == ""

    def test_validate_source_valid(self) -> None:
        renderer = TemplateRenderer()
        renderer.validate_source("{{ project.name }}")

    def test_validate_source_invalid(self) -> None:
        renderer = TemplateRenderer()
        with pytest.raises(TemplateRenderError, match="syntax error"):
            renderer.validate_source("{% if %}")

    def test_render_preserves_trailing_newline(self) -> None:
        renderer = TemplateRenderer()
        ctx = _make_context()
        result = renderer.render("hello\n", ctx)
        assert result.endswith("\n")


# =============================================================================
# Auto-Generated Header
# =============================================================================


class TestAutoGeneratedHeader:
    def test_python_header(self) -> None:
        header = auto_generated_header(language="python", generator_id="g")
        assert "AUTO-GENERATED FILE" in header
        assert header.startswith("#")
        assert "Generator: g" in header

    def test_yaml_header(self) -> None:
        header = auto_generated_header(language="yaml")
        assert header.startswith("#")

    def test_html_header(self) -> None:
        header = auto_generated_header(language="html")
        assert "<!--" in header
        assert "-->" in header

    def test_with_template_id(self) -> None:
        header = auto_generated_header(template_id="python.module")
        assert "Template: python.module" in header

    def test_with_source(self) -> None:
        header = auto_generated_header(source="test.py")
        assert "Source: test.py" in header

    def test_unknown_language(self) -> None:
        header = auto_generated_header(language="unknown")
        assert "AUTO-GENERATED FILE" in header


# =============================================================================
# Safety Policies
# =============================================================================


class TestValidateDestination:
    def test_valid_relative_path(self, tmp_path: Path) -> None:
        result = validate_destination(tmp_path, "sub/file.py", tmp_path)
        assert result.is_file() is False
        assert "sub" in str(result)

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafeDestinationError, match="traversal"):
            validate_destination(tmp_path, "../escape.py", tmp_path)

    def test_single_dot_dot(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafeDestinationError, match="traversal"):
            validate_destination(tmp_path, "..", tmp_path)

    def test_protected_git(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafeDestinationError, match="protected"):
            validate_destination(tmp_path, ".git/config", tmp_path)

    def test_protected_pycache(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafeDestinationError, match="protected"):
            validate_destination(tmp_path, "__pycache__/mod.py", tmp_path)

    def test_empty_path_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(UnsafeDestinationError, match="empty"):
            validate_destination(tmp_path, "", tmp_path)

    def test_escaping_project_root(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()
        dest = tmp_path / "output"
        dest.mkdir()
        with pytest.raises(UnsafeDestinationError, match="project root"):
            validate_destination(dest, "file.py", project)


class TestValidateNoSecrets:
    def test_no_secrets_passes(self) -> None:
        validate_no_secrets({"name": "hello", "count": 42})

    def test_empty_secret_passes(self) -> None:
        validate_no_secrets({"api_key": ""})

    def test_zero_secret_passes(self) -> None:
        validate_no_secrets({"token": 0})

    def test_false_secret_passes(self) -> None:
        validate_no_secrets({"password": False})

    def test_api_key_rejected(self) -> None:
        with pytest.raises(SecretContextError, match="api_key"):
            validate_no_secrets({"api_key": "sk-12345"})

    def test_token_rejected(self) -> None:
        with pytest.raises(SecretContextError, match="token"):
            validate_no_secrets({"auth_token": "abc"})

    def test_password_rejected(self) -> None:
        with pytest.raises(SecretContextError):
            validate_no_secrets({"password": "hunter2"})

    def test_secret_rejected(self) -> None:
        with pytest.raises(SecretContextError):
            validate_no_secrets({"secret": "xyz"})


# =============================================================================
# Planner
# =============================================================================


class TestGenerationPlanner:
    def test_plan_single_artifact(self) -> None:
        planner = GenerationPlanner()
        request = _make_request()
        plan = planner.plan(request, Path("/project"))
        assert len(plan.artifacts) == 1
        assert plan.is_valid is True

    def test_plan_multiple_artifacts(self) -> None:
        planner = GenerationPlanner()
        artifacts = (
            ArtifactSpec(relative_path="a.py", template_id="t"),
            ArtifactSpec(relative_path="b.py", template_id="t"),
        )
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        assert len(plan.artifacts) == 2

    def test_plan_empty_artifacts_rejected(self) -> None:
        planner = GenerationPlanner()
        request = GenerationRequest(
            generator_id="g",
            destination="out",
            context=_make_context(),
            artifacts=(),
        )
        with pytest.raises(GenerationValidationError, match="no artifacts"):
            planner.plan(request, Path("/project"))

    def test_plan_duplicate_destinations(self) -> None:
        planner = GenerationPlanner()
        artifacts = (
            ArtifactSpec(relative_path="a.py", template_id="t"),
            ArtifactSpec(relative_path="a.py", template_id="t"),
        )
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        has_dup = any(
            "duplicate" in str(i.message).lower()
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_dup

    def test_plan_absolute_path_warning(self) -> None:
        planner = GenerationPlanner()
        artifacts = (ArtifactSpec(relative_path="/abs.py", template_id="t"),)
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        has_error = any(
            i.severity == ValidationSeverity.ERROR
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_error

    def test_plan_empty_path(self) -> None:
        planner = GenerationPlanner()
        artifacts = (ArtifactSpec(relative_path="", template_id="t"),)
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        has_error = any(
            i.severity == ValidationSeverity.ERROR
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_error

    def test_plan_empty_template_id(self) -> None:
        planner = GenerationPlanner()
        artifacts = (ArtifactSpec(relative_path="a.py", template_id=""),)
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        has_error = any(
            "template_id" in str(i.message).lower() or "no template" in str(i.message).lower()
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_error

    def test_plan_unknown_template_warning(self) -> None:
        planner = GenerationPlanner()
        artifacts = (ArtifactSpec(relative_path="a.py", template_id="x.y"),)
        request = _make_request(artifacts=artifacts)
        ids = ("python.module",)
        plan = planner.plan(request, Path("/project"), template_ids=ids)
        has_warning = any(
            i.severity == ValidationSeverity.WARNING
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_warning

    def test_plan_traversal_in_path(self) -> None:
        planner = GenerationPlanner()
        artifacts = (ArtifactSpec(relative_path="../escape.py", template_id="t"),)
        request = _make_request(artifacts=artifacts)
        plan = planner.plan(request, Path("/project"))
        has_error = any(
            "traversal" in str(i.message).lower()
            for i in plan.issues
            if isinstance(i, ValidationIssue)
        )
        assert has_error

    def test_plan_preserves_dry_run(self) -> None:
        planner = GenerationPlanner()
        request = _make_request(dry_run=True)
        plan = planner.plan(request, Path("/project"))
        assert plan.dry_run is True

    def test_plan_destination_root(self) -> None:
        planner = GenerationPlanner()
        request = _make_request(destination="out/sub")
        plan = planner.plan(request, Path("/project"))
        assert plan.destination_root == (Path("/project") / "out" / "sub").resolve()


# =============================================================================
# Generator
# =============================================================================


class TestStaticGenerator:
    def test_generator_id(self) -> None:
        gen = StaticGenerator()
        assert gen.generator_id == "static"

    def test_plan(self) -> None:
        gen = StaticGenerator()
        request = _make_request()
        plan = gen.plan(request, Path("/project"))
        assert plan.generator_id == "test-gen"
        assert len(plan.artifacts) == 1


class TestGeneratorABC:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            Generator()  # type: ignore[abstract]


# =============================================================================
# Generator Registry
# =============================================================================


class TestGeneratorRegistry:
    def test_register_and_resolve(self) -> None:
        registry = GeneratorRegistry()
        gen = StaticGenerator()
        registry.register(gen)
        assert registry.resolve("static") is gen

    def test_resolve_unknown(self) -> None:
        registry = GeneratorRegistry()
        with pytest.raises(CodeGenerationError, match="No generator"):
            registry.resolve("nonexistent")

    def test_duplicate_registration(self) -> None:
        registry = GeneratorRegistry()
        gen = StaticGenerator()
        registry.register(gen)
        with pytest.raises(CodeGenerationError, match="already registered"):
            registry.register(gen)

    def test_contains(self) -> None:
        registry = GeneratorRegistry()
        assert registry.contains("static") is False
        registry.register(StaticGenerator())
        assert registry.contains("static") is True

    def test_generator_ids(self) -> None:
        registry = GeneratorRegistry()
        registry.register(StaticGenerator())
        ids = registry.generator_ids()
        assert "static" in ids

    def test_convenience_plan(self) -> None:
        registry = GeneratorRegistry()
        registry.register(StaticGenerator())
        request = _make_request(generator_id="static")
        plan = registry.plan(request, project_root=Path("/project"))
        assert len(plan.artifacts) == 1


# =============================================================================
# Generation Engine
# =============================================================================


class TestGenerationEngine:
    def test_successful_generation(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(
            template_repository=repo,
            project_root=tmp_path,
        )

        request = _make_request(destination="output")
        report = engine.generate(request)

        assert report.success is True
        assert report.generated_count == 1

        output_file = output_dir / "hello.py"
        assert output_file.is_file()
        content = output_file.read_text(encoding="utf-8")
        assert "Test Project" in content

    def test_generation_multiple_artifacts(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        artifacts = (
            ArtifactSpec(
                relative_path="mod.py",
                template_id="python.module",
                name="mod",
            ),
            ArtifactSpec(
                relative_path="pkg.py",
                template_id="python.package",
                name="pkg",
                description="A package",
            ),
        )
        request = _make_request(artifacts=artifacts, destination="output")
        report = engine.generate(request)

        assert report.success is True
        assert report.generated_count == 2
        assert (output_dir / "mod.py").is_file()
        assert (output_dir / "pkg.py").is_file()

    def test_dry_run_no_writes(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output", dry_run=True)
        report = engine.generate(request)

        assert report.dry_run is True
        assert not (output_dir / "hello.py").exists()

    def test_unchanged_detection(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output")
        report1 = engine.generate(request)
        assert report1.generated_count == 1

        report2 = engine.generate(request)
        assert report2.unchanged_count == 1

    def test_conflict_detection(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        (output_dir / "hello.py").write_text(
            "old content", encoding="utf-8"
        )

        request = _make_request(destination="output")
        report = engine.generate(request)

        assert report.success is False
        assert report.conflict_count == 1

    def test_overwrite_policy_allowed(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        (output_dir / "hello.py").write_text(
            "old content", encoding="utf-8"
        )

        request = _make_request(
            destination="output",
            overwrite=OverwritePolicy.ALLOWED,
        )
        report = engine.generate(request)

        assert report.overwritten_count == 1
        content = (output_dir / "hello.py").read_text(encoding="utf-8")
        assert "Test Project" in content
        assert "old content" not in content

    def test_partial_failure(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        artifacts = (
            ArtifactSpec(
                relative_path="good.py",
                template_id="python.module",
                name="good",
            ),
            ArtifactSpec(
                relative_path="bad.py",
                template_id="python.nonexistent",
                name="bad",
            ),
        )
        request = _make_request(artifacts=artifacts, destination="output")
        report = engine.generate(request)

        assert report.success is False
        assert report.failed_count >= 1

    def test_report_summary(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output")
        report = engine.generate(request)
        assert "created" in report.summary.lower()

    def test_plan_only(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output")
        plan = engine.plan_only(request)
        assert isinstance(plan, GenerationPlan)
        assert len(plan.artifacts) == 1

    def test_invalid_plan_returns_error_report(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = GenerationRequest(
            generator_id="g",
            destination="out",
            context=_make_context(),
            artifacts=(),
        )
        report = engine.generate(request)
        assert report.success is False
        assert report.failed_count >= 1


class TestGenerationEngineDeterminism:
    def test_same_output_byte_for_byte(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        engine.generate(_make_request(destination="output"))
        first = (output_dir / "hello.py").read_text(encoding="utf-8")

        engine.generate(_make_request(destination="output"))
        second = (output_dir / "hello.py").read_text(encoding="utf-8")

        assert first == second


class TestGenerationEngineFilesystemIntegration:
    def test_uses_filesystem_module(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output")
        engine.generate(request)

        from Engineering.core.filesystem import is_file

        assert is_file(output_dir / "hello.py")

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        artifacts = (
            ArtifactSpec(
                relative_path="deep/nested/file.py",
                template_id="python.module",
                name="file",
            ),
        )
        request = _make_request(artifacts=artifacts, destination="output")
        report = engine.generate(request)

        assert report.generated_count == 1
        assert (tmp_path / "output" / "deep" / "nested" / "file.py").is_file()


# =============================================================================
# End-to-End Demonstration
# =============================================================================


class TestEndToEndDemonstration:
    """
    Proves the entire generation pipeline:

    Request → Context → Template → Renderer → Artifact → Plan →
    Safety Validation → Filesystem → Report
    """

    def test_full_pipeline(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        generator_info = GeneratorInfo(
            generator_id="demo-generator",
            name="Demo",
            version="1.0.0",
        )
        project_info = _make_project_info()

        context = GenerationContext(
            project=project_info,
            generator=generator_info,
            artifact=ArtifactInfo(name="demo_module", description="A demo module"),
            values={"custom_field": "test_value"},
        )

        artifacts = (
            ArtifactSpec(
                relative_path="demo/module.py",
                template_id="python.module",
                artifact_type="source",
                name="demo_module",
                description="A demo module",
                values={"custom_field": "test_value"},
            ),
            ArtifactSpec(
                relative_path="demo/config.yaml",
                template_id="yaml.config",
                artifact_type="config",
                name="config",
            ),
        )

        request = GenerationRequest(
            generator_id="demo-generator",
            destination="output",
            context=context,
            artifacts=artifacts,
            overwrite=OverwritePolicy.NEVER,
            dry_run=False,
        )

        report = engine.generate(request)

        assert report.success is True
        assert report.generated_count == 2
        assert not report.dry_run
        assert "created" in report.summary.lower()

        module_file = output_dir / "demo" / "module.py"
        assert module_file.is_file()
        module_content = module_file.read_text(encoding="utf-8")
        assert "Test Project" in module_content
        assert "1.0.0" in module_content

        config_file = output_dir / "demo" / "config.yaml"
        assert config_file.is_file()
        config_content = config_file.read_text(encoding="utf-8")
        assert "Test Project" in config_content

    def test_pipeline_dry_run(self, tmp_path: Path) -> None:
        templates_root = _create_template_dir(tmp_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        repo = DirectoryTemplateRepository(templates_root)
        engine = GenerationEngine(template_repository=repo, project_root=tmp_path)

        request = _make_request(destination="output", dry_run=True)
        report = engine.generate(request)

        assert report.dry_run is True
        assert report.generated_count == 1
        assert not (output_dir / "hello.py").exists()


# =============================================================================
# CLI Integration
# =============================================================================


class TestCodeGenerationCLI:
    def test_generate_help_still_works(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "provider" in result.output
        assert "plugin" in result.output

    def test_generate_command_still_placeholder(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["generate"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output.lower()
