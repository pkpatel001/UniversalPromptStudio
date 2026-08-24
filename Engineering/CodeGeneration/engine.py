"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Generation Engine

This module provides the central GenerationEngine that executes
GenerationPlans through a controlled, multi-phase pipeline:

  1. Plan validation (preflight)
  2. Template resolution and rendering
  3. Path safety validation
  4. Conflict detection
  5. Filesystem execution
  6. Report generation

The engine never constructs plans — it receives validated
GenerationPlan instances from generators or the planner.

Public API
----------
from Engineering.CodeGeneration.engine import GenerationEngine

engine = GenerationEngine(
    template_repository=repo,
    project_root=paths.root,
)
report = engine.generate(request)

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from Engineering.core.exceptions import GenerationValidationError
from Engineering.core.filesystem import ensure_directory, read_text, write_text

from .models import (
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
)
from .planner import GenerationPlanner
from .policies import validate_destination, validate_no_secrets
from .renderer import TemplateRenderer
from .templates import TemplateRepository

__all__ = ["GenerationEngine"]


class GenerationEngine:
    """
    Executes generation plans through a controlled pipeline.

    The engine owns:
    * Template resolution (via repository)
    * Rendering (via renderer)
    * Path safety (via policies)
    * Conflict detection
    * Filesystem writes (via core/filesystem)
    * Report aggregation

    The engine does NOT own:
    * Plan construction (generators/planner)
    * Template storage (template repository)
    * CLI presentation
    """

    def __init__(
        self,
        template_repository: TemplateRepository,
        project_root: Path,
        renderer: TemplateRenderer | None = None,
        planner: GenerationPlanner | None = None,
    ) -> None:
        self._repository = template_repository
        self._project_root = project_root.resolve()
        self._renderer = renderer or TemplateRenderer()
        self._planner = planner or GenerationPlanner()

    @property
    def project_root(self) -> Path:
        """Return the resolved project root."""

        return self._project_root

    def generate(self, request: GenerationRequest) -> GenerationReport:
        """
        Execute a full generation cycle for a request.

        Pipeline: plan → preflight → render → safety → write → report.

        Parameters
        ----------
        request
            The generation request.

        Returns
        -------
        GenerationReport
            Structured report of all artifact outcomes.
        """

        try:
            plan = self._planner.plan(
                request,
                self._project_root,
                template_ids=self._repository.template_ids(),
            )
        except GenerationValidationError as exc:
            return GenerationReport(
                results=(
                    ArtifactResult(
                        state=ArtifactState.FAILED,
                        relative_path="",
                        reason=str(exc),
                    ),
                ),
                dry_run=request.dry_run,
            )

        if not plan.is_valid:
            return self._build_error_report(plan)

        validate_no_secrets(request.context.values)

        preflight_items = self._preflight(plan)
        preflight_results = [item[0] for item in preflight_items]

        has_failures = any(
            item[0].state == ArtifactState.FAILED for item in preflight_items
        )
        if has_failures:
            return GenerationReport(
                results=tuple(preflight_results),
                dry_run=plan.dry_run,
            )

        if plan.dry_run:
            return GenerationReport(
                results=tuple(preflight_results),
                dry_run=True,
            )

        write_results = self._execute(plan, preflight_items)

        return GenerationReport(
            results=tuple(write_results),
            dry_run=False,
        )

    def plan_only(self, request: GenerationRequest) -> GenerationPlan:
        """
        Construct and validate a plan without rendering or writing.

        Parameters
        ----------
        request
            The generation request.

        Returns
        -------
        GenerationPlan
            Validated plan.
        """

        return self._planner.plan(
            request,
            self._project_root,
            template_ids=self._repository.template_ids(),
        )

    def preview(self, request: GenerationRequest) -> tuple[GeneratedArtifact, ...]:
        """Render and path-validate every artifact without inspecting or writing outputs."""

        plan = self._planner.plan(
            request,
            self._project_root,
            template_ids=self._repository.template_ids(),
        )
        if not plan.is_valid:
            raise GenerationValidationError("Generation preview rejected an invalid plan.")
        validate_no_secrets(request.context.values)
        items = self._preflight(plan)
        artifacts: list[GeneratedArtifact] = []
        for result, generated, _destination in items:
            if result.state == ArtifactState.FAILED or generated is None:
                raise GenerationValidationError(
                    "Generation preview failed during rendering or path validation."
                )
            artifacts.append(generated)
        return tuple(artifacts)

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------

    def _preflight(
        self, plan: GenerationPlan
    ) -> list[tuple[ArtifactResult, GeneratedArtifact | None, Path | None]]:
        """
        Resolve templates, render content, and validate paths for
        all planned artifacts without writing.
        """

        preflight_items: list[
            tuple[ArtifactResult, GeneratedArtifact | None, Path | None]
        ] = []

        for spec in plan.artifacts:
            try:
                generated = self._render_artifact(plan, spec)
                destination = validate_destination(
                    plan.destination_root,
                    spec.relative_path,
                    self._project_root,
                )
                result = ArtifactResult(
                    state=ArtifactState.CREATED,
                    relative_path=spec.relative_path,
                    artifact_type=spec.artifact_type,
                    source_template=spec.template_id,
                )
                preflight_items.append((result, generated, destination))
            except Exception as exc:
                result = ArtifactResult(
                    state=ArtifactState.FAILED,
                    relative_path=spec.relative_path,
                    artifact_type=spec.artifact_type,
                    source_template=spec.template_id,
                    reason=str(exc),
                )
                preflight_items.append((result, None, None))

        return preflight_items

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render_artifact(
        self,
        plan: GenerationPlan,
        spec: ArtifactSpec,
    ) -> GeneratedArtifact:
        """Resolve template, build context, and render a single artifact."""

        validate_no_secrets(spec.values)

        template = self._repository.resolve(spec.template_id)

        base = plan.context

        values: dict[str, object] = {}
        if base is not None:
            values.update(dict(base.values))
        values.update(dict(spec.values))

        if base is not None:
            project_info = base.project
            generator_info = base.generator
        else:
            project_info = ProjectGenerationInfo(
                name="",
                short_name="",
                version="",
                company="",
                license="",
            )
            generator_info = GeneratorInfo(generator_id=plan.generator_id)

        context = GenerationContext(
            project=project_info,
            generator=generator_info,
            artifact=ArtifactInfo(
                name=spec.name or spec.relative_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
                description=spec.description,
            ),
            values=values,
        )

        content = self._renderer.render(template.source, context)

        return GeneratedArtifact(
            relative_path=spec.relative_path,
            content=content,
            artifact_type=spec.artifact_type,
            source_template=spec.template_id,
            metadata={"language": template.language},
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(
        self,
        plan: GenerationPlan,
        preflight_items: list[tuple[ArtifactResult, GeneratedArtifact | None, Path | None]],
    ) -> list[ArtifactResult]:
        """
        Execute writes for preflight-validated artifacts.
        """

        final_results: list[ArtifactResult] = []

        for spec, (preflight_result, generated, destination) in zip(
            plan.artifacts, preflight_items, strict=True
        ):
            failed = (
                preflight_result.state == ArtifactState.FAILED
                or generated is None
                or destination is None
            )
            if failed:
                final_results.append(preflight_result)
                continue

            assert generated is not None
            assert destination is not None

            result_state, reason = self._resolve_destination_state(
                destination, generated.content, plan
            )

            if result_state == ArtifactState.CREATED or result_state == ArtifactState.OVERWRITTEN:
                ensure_directory(destination.parent)
                write_text(destination, generated.content)

            final_results.append(
                ArtifactResult(
                    state=result_state,
                    relative_path=spec.relative_path,
                    artifact_type=spec.artifact_type,
                    source_template=spec.template_id,
                    reason=reason,
                )
            )

        return final_results

    def _resolve_destination_state(
        self,
        destination: Path,
        content: str,
        plan: GenerationPlan,
    ) -> tuple[ArtifactState, str]:
        """
        Determine the artifact state based on destination existence
        and content comparison.
        """

        if not destination.exists():
            return ArtifactState.CREATED, ""

        try:
            existing = read_text(destination)
        except Exception:
            return ArtifactState.FAILED, "Cannot read existing destination file."

        if existing == content:
            return ArtifactState.UNCHANGED, "Destination is identical."

        if plan.dry_run:
            return ArtifactState.CONFLICT, "Destination differs (dry-run)."

        if plan.overwrite == OverwritePolicy.ALLOWED:
            return ArtifactState.OVERWRITTEN, "Destination differs; overwrite permitted."

        return ArtifactState.CONFLICT, "Destination differs; overwrite policy is NEVER."

    # ------------------------------------------------------------------
    # Error reporting
    # ------------------------------------------------------------------

    def _build_error_report(self, plan: GenerationPlan) -> GenerationReport:
        """Build a report from a plan that failed preflight validation."""

        results = [
            ArtifactResult(
                state=ArtifactState.FAILED,
                relative_path=spec.relative_path,
                artifact_type=spec.artifact_type,
                source_template=spec.template_id,
                reason="Plan validation failed.",
            )
            for spec in plan.artifacts
        ]

        return GenerationReport(
            results=tuple(results),
            dry_run=plan.dry_run,
        )
