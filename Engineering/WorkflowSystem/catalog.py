"""Deterministic non-executing catalog for compatible workflows."""

from __future__ import annotations

from collections.abc import Iterable

from Engineering.core.exceptions import WorkflowError

from .compatibility import WorkflowSdkContract
from .models import WorkflowId, WorkflowRecord, WorkflowVersion
from .validation import require_vendor_id


class WorkflowCatalog:
    """Register and resolve workflow identity/version/operation metadata."""

    def __init__(
        self,
        records: Iterable[WorkflowRecord] = (),
        sdk_contract: WorkflowSdkContract | None = None,
    ) -> None:
        self._records: dict[tuple[str, str], WorkflowRecord] = {}
        self._sdk_contract = sdk_contract or WorkflowSdkContract()
        for record in records:
            self.register(record)

    def register(self, record: WorkflowRecord) -> None:
        issue = self._sdk_contract.issue_for(record)
        if issue is not None:
            raise WorkflowError(issue.message)
        key = (record.workflow_id, record.version)
        if key in self._records:
            raise WorkflowError(
                f"Duplicate workflow identity: {record.workflow_id} version {record.version}."
            )
        self._records[key] = record

    def resolve(
        self,
        workflow_id: str,
        version: str | None = None,
        *,
        operations: Iterable[str] = (),
    ) -> WorkflowRecord:
        WorkflowId(workflow_id)
        if version is not None:
            WorkflowVersion(version)
        required = frozenset(operations)
        for operation in required:
            require_vendor_id(operation, "Workflow operation id")
        candidates = [
            record
            for (registered_id, registered_version), record in self._records.items()
            if registered_id == workflow_id
            and (version is None or registered_version == version)
            and required.issubset(record.operations)
        ]
        if not candidates:
            suffix = f" version {version}" if version is not None else ""
            operation_suffix = " with operations " + ", ".join(sorted(required)) if required else ""
            raise WorkflowError(
                f"Unknown compatible workflow: {workflow_id}{suffix}{operation_suffix}."
            )
        return max(candidates, key=lambda item: item.manifest.metadata.version.parsed)

    def records_for(self, workflow_id: str) -> tuple[WorkflowRecord, ...]:
        WorkflowId(workflow_id)
        return tuple(item for item in self.records if item.workflow_id == workflow_id)

    def supporting(self, operations: Iterable[str]) -> tuple[WorkflowRecord, ...]:
        required = frozenset(operations)
        if not required:
            raise WorkflowError("At least one workflow operation is required for filtering.")
        for operation in required:
            require_vendor_id(operation, "Workflow operation id")
        return tuple(record for record in self.records if required.issubset(record.operations))

    def available_versions(self, workflow_id: str) -> tuple[str, ...]:
        return tuple(item.version for item in self.records_for(workflow_id))

    @property
    def records(self) -> tuple[WorkflowRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda item: (
                    item.workflow_id,
                    item.manifest.metadata.version.parsed,
                    item.root_id,
                    item.relative_path,
                ),
            )
        )
