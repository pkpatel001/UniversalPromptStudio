"""Controlled E-017.2 self-generation execution and reproducibility checks."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from Engineering.CodeGeneration import (
    ArtifactInfo,
    DirectoryTemplateRepository,
    GeneratedArtifact,
    GenerationContext,
    GenerationEngine,
    GenerationRequest,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import SelfGenerationError
from Engineering.Templates import (
    ArtifactManifest,
    ArtifactManifestBuilder,
    DirectoryTemplateDefinitionRepository,
    TemplateArtifactService,
    TemplateDefinition,
    TemplateDefinitionValidator,
)

from .inventory import derive_self_generation_artifacts
from .models import (
    SelfGenerationArtifact,
    SelfGenerationExecutionResult,
    SelfGenerationPlan,
    SelfGenerationRequest,
    SelfGenerationTemplateKey,
    SelfGenerationVerificationIssue,
    SelfGenerationVerificationReport,
)
from .planner import SelfGenerationPlanner
from .preconditions import SelfGenerationPreconditionChecker

SELF_GENERATION_TEMPLATE_ID = "engineering.subsystem-basic"
SELF_GENERATION_CLI_TEMPLATE_ID = "engineering.subsystem-with-cli"
SELF_GENERATION_TEMPLATE_VERSION = "1.0.0"
SELF_GENERATION_MANIFEST_NAME = ".ups-artifact-manifest.json"

_SOURCE_BY_KEY: dict[SelfGenerationTemplateKey, str] = {
    SelfGenerationTemplateKey.PACKAGE_INIT: "self_generation.package_init",
    SelfGenerationTemplateKey.MODULE: "self_generation.module",
    SelfGenerationTemplateKey.TEST: "self_generation.test",
    SelfGenerationTemplateKey.DOCUMENTATION: "self_generation.readme",
    SelfGenerationTemplateKey.CLI_ADAPTER: "self_generation.cli_adapter",
}


class SelfGenerationService:
    """Execute accepted plans through E-009/E-008 and verify reproducibility."""

    def __init__(
        self,
        project_root: Path,
        project: ProjectGenerationInfo,
        definitions: DirectoryTemplateDefinitionRepository,
        sources: DirectoryTemplateRepository,
    ) -> None:
        self._project_root = project_root.resolve()
        self._project = project
        self._definitions = definitions
        self._sources = sources
        self._artifact_service = TemplateArtifactService(TemplateDefinitionValidator(sources))
        self._engine = GenerationEngine(sources, self._project_root)

    @classmethod
    def built_in(
        cls,
        project_root: Path,
        project: ProjectGenerationInfo,
    ) -> SelfGenerationService:
        """Create the service from package-bundled approved templates."""

        templates_root = Path(__file__).resolve().parents[1] / "Templates"
        sources = DirectoryTemplateRepository(templates_root / "CodeGeneration")
        definitions = DirectoryTemplateDefinitionRepository(
            templates_root / "Definitions",
            TemplateDefinitionValidator(sources),
        )
        return cls(project_root, project, definitions, sources)

    def execute(self, plan: SelfGenerationPlan) -> SelfGenerationExecutionResult:
        """Execute one current ready plan with rollback on every later failure."""

        current = SelfGenerationPlanner(self._project_root).plan(plan.request)
        if not current.ready or current != plan:
            raise SelfGenerationError(
                "Self-generation execution requires the current unmodified ready plan."
            )
        definition = self._definition(plan.request)
        request = self._generation_request(definition, plan.request)
        preview = self._stable_preview(request)
        self._require_preview_matches_plan(preview, plan.artifacts)

        manifest_path = self._manifest_path(plan.request)
        if manifest_path.exists() or manifest_path.is_symlink():
            raise SelfGenerationError(
                "Self-generation artifact manifest already exists; overwrite is forbidden."
            )

        preexisting_directories = self._preexisting_directories(plan.artifacts, manifest_path)
        try:
            report = self._engine.generate(request)
            if not report.success:
                raise SelfGenerationError("The E-008 generation report rejected the transaction.")
            manifest = ArtifactManifestBuilder().build(definition, report, self._project_root)
            manifest.write(manifest_path)
            verification = self.check(plan.request)
            if not verification.passed:
                raise SelfGenerationError(
                    "Post-generation structure, import, or reproducibility verification failed."
                )
            return SelfGenerationExecutionResult(
                plan=plan,
                generation_report=report,
                manifest=manifest,
                manifest_path=manifest_path,
                verification=verification,
            )
        except Exception as exc:
            rollback_issues = self._rollback(plan.artifacts, manifest_path, preexisting_directories)
            if rollback_issues:
                raise SelfGenerationError(
                    "Self-generation failed and transactional rollback was incomplete."
                ) from exc
            raise SelfGenerationError(
                "Self-generation transaction failed; generated changes were rolled back."
            ) from exc

    def check(self, request: SelfGenerationRequest) -> SelfGenerationVerificationReport:
        """Verify current outputs against the allowlist, manifest, and templates."""

        issues: list[SelfGenerationVerificationIssue] = []
        artifacts = derive_self_generation_artifacts(request)
        root_marker = self._project_root / "pyproject.toml"
        if not root_marker.is_file() or root_marker.is_symlink():
            issues.append(
                SelfGenerationVerificationIssue(
                    "project-root.invalid",
                    "The project root marker is missing or unsafe.",
                    "pyproject.toml",
                )
            )
        prerequisites = SelfGenerationPreconditionChecker().check(self._project_root)
        for result in prerequisites.results:
            for missing in result.missing_paths:
                issues.append(
                    SelfGenerationVerificationIssue(
                        f"precondition.{result.precondition.milestone.value.lower()}.missing",
                        "Required Engineering milestone evidence is unavailable.",
                        missing.as_posix(),
                    )
                )

        try:
            definition = self._definition(request)
            generation_request = self._generation_request(definition, request)
            preview = self._stable_preview(generation_request)
            self._require_preview_matches_plan(preview, artifacts)
        except Exception:
            preview = ()
            definition = None
            issues.append(
                SelfGenerationVerificationIssue(
                    "template.preview-failed",
                    "Approved templates could not be rendered deterministically.",
                )
            )

        expected_content = {artifact.relative_path: artifact.content for artifact in preview}
        for artifact in artifacts:
            relative = artifact.relative_path.as_posix()
            path = self._project_root.joinpath(*artifact.relative_path.parts)
            if self._has_symlink_component(artifact):
                issues.append(
                    SelfGenerationVerificationIssue(
                        "artifact.symlink",
                        "Generated artifact traverses a symlinked component.",
                        relative,
                    )
                )
                continue
            if not path.is_file():
                issues.append(
                    SelfGenerationVerificationIssue(
                        "artifact.missing",
                        "Generated artifact is missing.",
                        relative,
                    )
                )
                continue
            expected = expected_content.get(relative)
            try:
                actual = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                issues.append(
                    SelfGenerationVerificationIssue(
                        "artifact.unreadable",
                        "Generated artifact cannot be read as UTF-8.",
                        relative,
                    )
                )
                continue
            if expected is not None and actual != expected:
                issues.append(
                    SelfGenerationVerificationIssue(
                        "artifact.template-drift",
                        "Generated artifact differs from the current approved template.",
                        relative,
                    )
                )

        manifest_path = self._manifest_path(request)
        manifest: ArtifactManifest | None = None
        try:
            if manifest_path.is_symlink():
                raise SelfGenerationError("Manifest must not be a symlink.")
            manifest = ArtifactManifest.read(manifest_path)
        except Exception:
            issues.append(
                SelfGenerationVerificationIssue(
                    "manifest.invalid",
                    "Artifact manifest is missing, unsafe, or invalid.",
                    manifest_path.relative_to(self._project_root).as_posix(),
                )
            )
        if manifest is not None and definition is not None:
            issues.extend(self._manifest_issues(manifest, definition, artifacts))
            for issue in manifest.verify(self._project_root).issues:
                issues.append(
                    SelfGenerationVerificationIssue(
                        "manifest.hash-drift",
                        issue.message,
                        issue.relative_path,
                    )
                )

        issues.extend(self._structural_issues(request, artifacts))
        return SelfGenerationVerificationReport(
            tuple(sorted(set(issues), key=lambda item: (item.code, item.location)))
        )

    def _generation_request(
        self,
        definition: TemplateDefinition,
        request: SelfGenerationRequest,
    ) -> GenerationRequest:
        values = self._values(request)
        context = GenerationContext(
            project=self._project,
            generator=GeneratorInfo(
                generator_id=definition.template_id,
                name=definition.metadata.name,
                version=definition.version,
            ),
            artifact=ArtifactInfo(
                name=request.display_name,
                description=request.description,
            ),
        )
        return self._artifact_service.build_request(
            definition,
            destination="",
            context=context,
            values=values,
            overwrite=OverwritePolicy.NEVER,
            dry_run=False,
        )

    @staticmethod
    def _values(request: SelfGenerationRequest) -> dict[str, object]:
        class_name = "".join(part.capitalize() for part in request.module_name.split("_"))
        return {
            "package_name": request.package_name,
            "module_name": request.module_name,
            "class_name": class_name,
            "display_name": request.display_name,
            "description": request.description,
        }

    def _definition(self, request: SelfGenerationRequest) -> TemplateDefinition:
        template_id = (
            SELF_GENERATION_CLI_TEMPLATE_ID
            if request.include_cli_adapter
            else SELF_GENERATION_TEMPLATE_ID
        )
        return self._definitions.resolve(template_id, SELF_GENERATION_TEMPLATE_VERSION)

    def _stable_preview(self, request: GenerationRequest) -> tuple[GeneratedArtifact, ...]:
        first = self._engine.preview(request)
        second = self._engine.preview(request)
        if first != second:
            raise SelfGenerationError(
                "Approved self-generation templates rendered nondeterministically."
            )
        return first

    @staticmethod
    def _require_preview_matches_plan(
        preview: tuple[GeneratedArtifact, ...],
        artifacts: tuple[SelfGenerationArtifact, ...],
    ) -> None:
        expected = tuple(
            (
                artifact.relative_path.as_posix(),
                artifact.artifact_type.value,
                _SOURCE_BY_KEY[artifact.template_key],
            )
            for artifact in artifacts
        )
        actual = tuple(
            (artifact.relative_path, artifact.artifact_type, artifact.source_template)
            for artifact in preview
        )
        if actual != expected:
            raise SelfGenerationError(
                "Approved template outputs do not match the accepted allowlisted plan."
            )

    def _manifest_path(self, request: SelfGenerationRequest) -> Path:
        return (
            self._project_root
            / "Engineering"
            / request.package_name
            / SELF_GENERATION_MANIFEST_NAME
        )

    def _manifest_issues(
        self,
        manifest: ArtifactManifest,
        definition: TemplateDefinition,
        artifacts: tuple[SelfGenerationArtifact, ...],
    ) -> tuple[SelfGenerationVerificationIssue, ...]:
        issues: list[SelfGenerationVerificationIssue] = []
        if (
            manifest.template_id != definition.template_id
            or manifest.template_version != definition.version
        ):
            issues.append(
                SelfGenerationVerificationIssue(
                    "manifest.template-drift",
                    "Artifact manifest template identity or version differs.",
                    self._manifest_path_for_location(artifacts),
                )
            )
        expected = tuple(
            sorted(
                (
                    artifact.relative_path.as_posix(),
                    artifact.artifact_type.value,
                    _SOURCE_BY_KEY[artifact.template_key],
                )
                for artifact in artifacts
            )
        )
        actual = tuple(
            (
                entry.relative_path,
                entry.artifact_type,
                entry.source_template,
            )
            for entry in manifest.artifacts
        )
        if actual != expected:
            issues.append(
                SelfGenerationVerificationIssue(
                    "manifest.inventory-drift",
                    "Artifact manifest entries differ from the allowlisted plan.",
                    self._manifest_path_for_location(artifacts),
                )
            )
        return tuple(issues)

    @staticmethod
    def _manifest_path_for_location(
        artifacts: tuple[SelfGenerationArtifact, ...],
    ) -> str:
        package = artifacts[0].relative_path.parent
        return (package / SELF_GENERATION_MANIFEST_NAME).as_posix()

    def _structural_issues(
        self,
        request: SelfGenerationRequest,
        artifacts: tuple[SelfGenerationArtifact, ...],
    ) -> tuple[SelfGenerationVerificationIssue, ...]:
        issues: list[SelfGenerationVerificationIssue] = []
        for artifact in artifacts:
            if artifact.relative_path.suffix != ".py":
                continue
            relative = artifact.relative_path.as_posix()
            path = self._project_root.joinpath(*artifact.relative_path.parts)
            if not path.is_file() or path.is_symlink():
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=relative)
                compile(tree, relative, "exec")
            except (OSError, UnicodeError, SyntaxError, ValueError):
                issues.append(
                    SelfGenerationVerificationIssue(
                        "python.structure-invalid",
                        "Generated Python source does not parse or compile.",
                        relative,
                    )
                )
        if issues:
            return tuple(issues)

        package_init = self._project_root / "Engineering" / request.package_name / "__init__.py"
        class_name = str(self._values(request)["class_name"])
        namespace = f"_ups_selfcheck_{request.package_name.lower()}"
        previous_bytecode = sys.dont_write_bytecode
        loaded: ModuleType | None = None
        try:
            spec = importlib.util.spec_from_file_location(
                namespace,
                package_init,
                submodule_search_locations=[str(package_init.parent)],
            )
            if spec is None or spec.loader is None:
                raise ImportError("No isolated package loader.")
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[namespace] = loaded
            sys.dont_write_bytecode = True
            spec.loader.exec_module(loaded)
            exported = getattr(loaded, class_name, None)
            if not isinstance(exported, type):
                raise ImportError("Expected generated class is not exported.")
        except Exception:
            issues.append(
                SelfGenerationVerificationIssue(
                    "python.import-failed",
                    "Generated package failed isolated import verification.",
                    package_init.relative_to(self._project_root).as_posix(),
                )
            )
        finally:
            sys.dont_write_bytecode = previous_bytecode
            for module_name in tuple(sys.modules):
                if module_name == namespace or module_name.startswith(f"{namespace}."):
                    sys.modules.pop(module_name, None)
        return tuple(issues)

    def _has_symlink_component(self, artifact: SelfGenerationArtifact) -> bool:
        current = self._project_root
        for part in artifact.relative_path.parts:
            current /= part
            if current.is_symlink():
                return True
        return False

    def _preexisting_directories(
        self,
        artifacts: tuple[SelfGenerationArtifact, ...],
        manifest_path: Path,
    ) -> frozenset[Path]:
        directories: set[Path] = set()
        for path in (
            *(self._project_root.joinpath(*item.relative_path.parts) for item in artifacts),
            manifest_path,
        ):
            current = path.parent
            while current != self._project_root:
                if current.is_dir():
                    directories.add(current)
                current = current.parent
        return frozenset(directories)

    def _rollback(
        self,
        artifacts: tuple[SelfGenerationArtifact, ...],
        manifest_path: Path,
        preexisting_directories: frozenset[Path],
    ) -> tuple[str, ...]:
        issues: list[str] = []
        targets = [
            self._project_root.joinpath(*artifact.relative_path.parts) for artifact in artifacts
        ]
        targets.append(manifest_path)
        for path in reversed(targets):
            try:
                if path.is_symlink():
                    issues.append(path.as_posix())
                elif path.is_file():
                    path.unlink()
                elif path.exists():
                    issues.append(path.as_posix())
            except OSError:
                issues.append(path.as_posix())

        directories = {
            parent
            for target in targets
            for parent in target.parents
            if parent != self._project_root
            and self._project_root in parent.parents
            and parent not in preexisting_directories
        }
        for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            try:
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
            except OSError:
                issues.append(directory.as_posix())
        return tuple(sorted(set(issues)))
