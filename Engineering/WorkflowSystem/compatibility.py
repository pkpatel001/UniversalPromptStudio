"""Workflow SDK API-level compatibility policy."""

from __future__ import annotations

from dataclasses import dataclass

from Engineering.core.exceptions import WorkflowError

from .manifest import WORKFLOW_SDK_API_LEVEL
from .models import (
    WorkflowIssue,
    WorkflowRecord,
    WorkflowSdkCompatibility,
    WorkflowSdkVersion,
)


@dataclass(frozen=True, slots=True)
class WorkflowSdkContract:
    """Inclusive workflow SDK API-level range supported by one host."""

    minimum_api_level: int = WORKFLOW_SDK_API_LEVEL
    maximum_api_level: int = WORKFLOW_SDK_API_LEVEL

    def __post_init__(self) -> None:
        if (
            type(self.minimum_api_level) is not int
            or type(self.maximum_api_level) is not int
            or self.minimum_api_level < 1
            or self.maximum_api_level < self.minimum_api_level
        ):
            raise WorkflowError(
                "Workflow SDK compatibility levels must be positive integers in ascending order."
            )

    def classify(self, version: WorkflowSdkVersion) -> WorkflowSdkCompatibility:
        if version.api_level < self.minimum_api_level:
            return WorkflowSdkCompatibility.TOO_OLD
        if version.api_level > self.maximum_api_level:
            return WorkflowSdkCompatibility.TOO_NEW
        return WorkflowSdkCompatibility.COMPATIBLE

    def issue_for(self, record: WorkflowRecord) -> WorkflowIssue | None:
        version = record.manifest.metadata.sdk_version
        compatibility = self.classify(version)
        if compatibility == WorkflowSdkCompatibility.COMPATIBLE:
            return None
        return WorkflowIssue(
            record.relative_path,
            "workflow.sdk.incompatible",
            (
                f"Workflow {record.workflow_id} version {record.version} declares "
                f"SDK API level {version.api_level} ({compatibility.value}); "
                f"supported levels are {self.minimum_api_level} through "
                f"{self.maximum_api_level}."
            ),
            record.root_id,
        )
