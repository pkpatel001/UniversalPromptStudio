"""Deterministic build manifests for E-010."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Engineering.core.filesystem import read_json, write_json

from .models import BuildPlan, BuildReport

BUILD_MANIFEST_NAME = "build-manifest.json"


@dataclass(frozen=True, slots=True)
class BuildManifest:
    """Machine-readable record of one successful build."""

    steps: tuple[dict[str, object], ...]
    schema_version: int = 1

    @classmethod
    def from_build(cls, plan: BuildPlan, report: BuildReport) -> BuildManifest:
        """Create a manifest from a matching plan and report."""

        results = {result.step_id: result for result in report.results}
        steps: list[dict[str, object]] = []
        for step_id in plan.step_ids:
            steps.append(
                {
                "step_id": step_id,
                "state": results[step_id].state.value,
                "message": results[step_id].message,
                "artifacts": list(results[step_id].artifacts),
                }
            )
        return cls(steps=tuple(steps))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "schema_version": self.schema_version,
            "steps": [dict(step) for step in self.steps],
        }

    def write(self, path: Path) -> None:
        """Write the manifest using canonical Engineering filesystem I/O."""

        write_json(path, self.to_dict())

    @classmethod
    def read(cls, path: Path) -> BuildManifest:
        """Load a schema-version-one build manifest."""

        data = read_json(path)
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported build manifest schema.")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not all(
            isinstance(step, dict) for step in raw_steps
        ):
            raise ValueError("Build manifest steps must be a list of mappings.")
        return cls(steps=tuple(dict(step) for step in raw_steps))
