"""Dependency-aware planner and executor for E-010 builds."""

from __future__ import annotations

from collections.abc import Sequence

from Engineering.core.exceptions import BuildError

from .models import BuildContext, BuildPlan, BuildReport, BuildState, BuildStepResult
from .steps import BuildStep


class BuildEngine:
    """Validate, plan, and execute registered build steps."""

    def __init__(self, steps: Sequence[BuildStep]) -> None:
        self._steps = {step.step_id: step for step in steps}
        if len(self._steps) != len(steps):
            raise BuildError("Build step identifiers must be unique.")

    def plan(
        self,
        *,
        targets: tuple[str, ...] | None = None,
        dry_run: bool = False,
    ) -> BuildPlan:
        """Produce a dependency-ordered plan for selected targets."""

        selected = targets or tuple(self._steps)
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id not in self._steps:
                raise BuildError(f"Unknown build step: {step_id!r}")
            if step_id in visiting:
                raise BuildError(f"Cyclic build dependency involving {step_id!r}")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in self._steps[step_id].dependencies:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)
            ordered.append(step_id)

        for target in selected:
            visit(target)
        return BuildPlan(tuple(ordered), dry_run=dry_run)

    def execute(self, plan: BuildPlan, context: BuildContext) -> BuildReport:
        """Execute a plan fail-fast and mark remaining steps skipped."""

        results: list[BuildStepResult] = []
        failed = False
        for step_id in plan.step_ids:
            if failed:
                results.append(
                    BuildStepResult(
                        step_id,
                        BuildState.SKIPPED,
                        "Skipped because a previous build step failed.",
                    )
                )
                continue
            try:
                result = self._steps[step_id].execute(context)
            except Exception as exc:
                result = BuildStepResult(step_id, BuildState.FAILED, str(exc))
            results.append(result)
            failed = result.state == BuildState.FAILED
        return BuildReport(tuple(results), dry_run=plan.dry_run)
