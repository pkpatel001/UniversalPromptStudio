"""Read-only theme discovery, compatibility, and catalog service."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .catalog import ThemeCatalog
from .compatibility import ThemeSdkContract
from .discovery import ThemeDiscoveryService
from .models import (
    ThemeDiscoveryRoot,
    ThemeInspectionReport,
    ThemeValidationReport,
)


class ThemeService:
    """Compose structural discovery and SDK compatibility classification."""

    def __init__(
        self,
        discovery: ThemeDiscoveryService | None = None,
        sdk_contract: ThemeSdkContract | None = None,
    ) -> None:
        self._discovery = discovery or ThemeDiscoveryService()
        self._sdk_contract = sdk_contract or ThemeSdkContract()

    def inspect(self, root: Path) -> ThemeInspectionReport:
        return self._discovery.inspect(root)

    def inspect_roots(self, roots: Iterable[ThemeDiscoveryRoot]) -> ThemeInspectionReport:
        return self._discovery.inspect_roots(roots)

    def validate(self, root: Path) -> ThemeValidationReport:
        return self._validate_inspection(self.inspect(root))

    def validate_roots(self, roots: Iterable[ThemeDiscoveryRoot]) -> ThemeValidationReport:
        return self._validate_inspection(self.inspect_roots(roots))

    def catalog(self, root: Path) -> ThemeCatalog:
        report = self.validate(root)
        if not report.passed:
            raise ThemeError(report.summary)
        return ThemeCatalog(report.records, self._sdk_contract)

    def catalog_roots(self, roots: Iterable[ThemeDiscoveryRoot]) -> ThemeCatalog:
        report = self.validate_roots(roots)
        if not report.passed:
            raise ThemeError(report.summary)
        return ThemeCatalog(report.records, self._sdk_contract)

    def _validate_inspection(self, inspection: ThemeInspectionReport) -> ThemeValidationReport:
        if not inspection.passed:
            return ThemeValidationReport(issues=inspection.issues)
        compatible = []
        issues = []
        for record in inspection.records:
            issue = self._sdk_contract.issue_for(record)
            if issue is None:
                compatible.append(record)
            else:
                issues.append(issue)
        return ThemeValidationReport(tuple(compatible), tuple(issues))


__all__ = ["ThemeService"]
