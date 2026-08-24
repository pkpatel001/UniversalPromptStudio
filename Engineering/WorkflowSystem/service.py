"""Read-only workflow discovery, compatibility, and catalog service."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import WorkflowError

from .catalog import WorkflowCatalog
from .compatibility import WorkflowSdkContract
from .discovery import WorkflowDiscoveryService
from .models import (
    WorkflowDiscoveryRoot,
    WorkflowInspectionReport,
    WorkflowValidationReport,
)


class WorkflowService:
    """Compose structural discovery and SDK compatibility classification."""

    def __init__(
        self,
        discovery: WorkflowDiscoveryService | None = None,
        sdk_contract: WorkflowSdkContract | None = None,
    ) -> None:
        self._discovery = discovery or WorkflowDiscoveryService()
        self._sdk_contract = sdk_contract or WorkflowSdkContract()

    def inspect(self, root: Path) -> WorkflowInspectionReport:
        return self._discovery.inspect(root)

    def inspect_roots(self, roots: Iterable[WorkflowDiscoveryRoot]) -> WorkflowInspectionReport:
        return self._discovery.inspect_roots(roots)

    def validate(self, root: Path) -> WorkflowValidationReport:
        return self._validate_inspection(self.inspect(root))

    def validate_roots(self, roots: Iterable[WorkflowDiscoveryRoot]) -> WorkflowValidationReport:
        return self._validate_inspection(self.inspect_roots(roots))

    def catalog(self, root: Path) -> WorkflowCatalog:
        report = self.validate(root)
        if not report.passed:
            raise WorkflowError(report.summary)
        return WorkflowCatalog(report.records, self._sdk_contract)

    def catalog_roots(self, roots: Iterable[WorkflowDiscoveryRoot]) -> WorkflowCatalog:
        report = self.validate_roots(roots)
        if not report.passed:
            raise WorkflowError(report.summary)
        return WorkflowCatalog(report.records, self._sdk_contract)

    def _validate_inspection(
        self, inspection: WorkflowInspectionReport
    ) -> WorkflowValidationReport:
        if not inspection.passed:
            return WorkflowValidationReport(issues=inspection.issues)
        compatible = []
        issues = []
        for record in inspection.records:
            issue = self._sdk_contract.issue_for(record)
            if issue is None:
                compatible.append(record)
            else:
                issues.append(issue)
        return WorkflowValidationReport(tuple(compatible), tuple(issues))
