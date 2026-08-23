"""Read-only provider discovery, compatibility, and catalog service."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import ProviderError

from .catalog import ProviderCatalog
from .compatibility import ProviderSdkContract
from .discovery import ProviderDiscoveryService
from .models import (
    ProviderDiscoveryRoot,
    ProviderInspectionReport,
    ProviderValidationReport,
)


class ProviderService:
    """Compose structural discovery and SDK compatibility classification."""

    def __init__(
        self,
        discovery: ProviderDiscoveryService | None = None,
        sdk_contract: ProviderSdkContract | None = None,
    ) -> None:
        self._discovery = discovery or ProviderDiscoveryService()
        self._sdk_contract = sdk_contract or ProviderSdkContract()

    def inspect(self, root: Path) -> ProviderInspectionReport:
        return self._discovery.inspect(root)

    def inspect_roots(self, roots: Iterable[ProviderDiscoveryRoot]) -> ProviderInspectionReport:
        return self._discovery.inspect_roots(roots)

    def validate(self, root: Path) -> ProviderValidationReport:
        return self._validate_inspection(self.inspect(root))

    def validate_roots(self, roots: Iterable[ProviderDiscoveryRoot]) -> ProviderValidationReport:
        return self._validate_inspection(self.inspect_roots(roots))

    def catalog(self, root: Path) -> ProviderCatalog:
        report = self.validate(root)
        if not report.passed:
            raise ProviderError(report.summary)
        return ProviderCatalog(report.records, self._sdk_contract)

    def catalog_roots(self, roots: Iterable[ProviderDiscoveryRoot]) -> ProviderCatalog:
        report = self.validate_roots(roots)
        if not report.passed:
            raise ProviderError(report.summary)
        return ProviderCatalog(report.records, self._sdk_contract)

    def _validate_inspection(
        self, inspection: ProviderInspectionReport
    ) -> ProviderValidationReport:
        if not inspection.passed:
            return ProviderValidationReport(issues=inspection.issues)
        compatible = []
        issues = []
        for record in inspection.records:
            issue = self._sdk_contract.issue_for(record)
            if issue is None:
                compatible.append(record)
            else:
                issues.append(issue)
        return ProviderValidationReport(tuple(compatible), tuple(issues))
