"""Controlled execution of E-009 definitions through the E-008 engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from Engineering.CodeGeneration import (
    DirectoryTemplateRepository,
    GenerationContext,
    GenerationEngine,
    GenerationReport,
    OverwritePolicy,
)

from .discovery import DirectoryTemplateDefinitionRepository, built_in_definition_repository
from .manifest import ArtifactManifest, ArtifactManifestBuilder
from .service import TemplateArtifactService
from .validation import TemplateDefinitionValidator

DEFAULT_MANIFEST_NAME = ".ups-artifact-manifest.json"


@dataclass(frozen=True, slots=True)
class TemplateExecutionResult:
    """Combined E-008 report and optional persisted E-009 manifest."""

    report: GenerationReport
    manifest: ArtifactManifest | None = None
    manifest_path: Path | None = None


class TemplateExecutor:
    """Resolve, validate, and execute template definitions safely."""

    def __init__(
        self,
        definition_repository: DirectoryTemplateDefinitionRepository,
        source_repository: DirectoryTemplateRepository,
        project_root: Path,
    ) -> None:
        self._definitions = definition_repository
        self._sources = source_repository
        self._project_root = project_root.resolve()
        self._validator = TemplateDefinitionValidator(source_repository)

    @classmethod
    def built_in(cls, project_root: Path) -> TemplateExecutor:
        """Create an executor using definitions and sources bundled with UPS."""

        templates_root = Path(__file__).resolve().parent
        return cls(
            built_in_definition_repository(),
            DirectoryTemplateRepository(templates_root / "CodeGeneration"),
            project_root,
        )

    def execute(
        self,
        template_id: str,
        *,
        destination: str,
        context: GenerationContext,
        version: str | None = None,
        values: Mapping[str, object] | None = None,
        overwrite: OverwritePolicy = OverwritePolicy.NEVER,
        dry_run: bool = False,
        write_manifest: bool = True,
    ) -> TemplateExecutionResult:
        """Execute a definition exclusively through the E-008 engine."""

        definition = self._definitions.resolve(template_id, version)
        request = TemplateArtifactService(self._validator).build_request(
            definition,
            destination=destination,
            context=context,
            values=values,
            overwrite=overwrite,
            dry_run=dry_run,
        )
        report = GenerationEngine(self._sources, self._project_root).generate(request)
        if dry_run or not report.success or not write_manifest:
            return TemplateExecutionResult(report=report)

        destination_root = (self._project_root / destination).resolve()
        manifest = ArtifactManifestBuilder().build(
            definition, report, destination_root
        )
        manifest_path = destination_root / DEFAULT_MANIFEST_NAME
        manifest.write(manifest_path)
        return TemplateExecutionResult(
            report=report,
            manifest=manifest,
            manifest_path=manifest_path,
        )
