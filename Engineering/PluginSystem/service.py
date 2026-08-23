"""Read-only application service for plugin inspection and cataloging."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import PluginError

from .catalog import PluginCatalog
from .compatibility import PluginSdkContract
from .dependencies import PluginDependencyResolver
from .discovery import PluginDiscoveryService
from .models import (
    PluginDiscoveryRoot,
    PluginInspectionReport,
    PluginValidationReport,
)


class PluginService:
    """Compose plugin discovery and deterministic catalog construction."""

    def __init__(
        self,
        discovery: PluginDiscoveryService | None = None,
        sdk_contract: PluginSdkContract | None = None,
        dependency_resolver: PluginDependencyResolver | None = None,
    ) -> None:
        self._discovery = discovery or PluginDiscoveryService()
        self._sdk_contract = sdk_contract or PluginSdkContract()
        self._dependency_resolver = dependency_resolver or PluginDependencyResolver()

    def inspect(self, root: Path) -> PluginInspectionReport:
        """Return all valid records and deterministic issues below root."""

        return self._discovery.inspect(root)

    def inspect_roots(
        self, roots: Iterable[PluginDiscoveryRoot]
    ) -> PluginInspectionReport:
        """Return structural discovery results across labeled roots."""

        return self._discovery.inspect_roots(roots)

    def validate(self, root: Path) -> PluginValidationReport:
        """Validate compatibility and dependencies below one root."""

        inspection = self.inspect(root)
        return self._validate_inspection(inspection)

    def validate_roots(
        self, roots: Iterable[PluginDiscoveryRoot]
    ) -> PluginValidationReport:
        """Validate compatibility and dependencies across labeled roots."""

        inspection = self.inspect_roots(roots)
        return self._validate_inspection(inspection)

    def catalog(self, root: Path) -> PluginCatalog:
        """Return a catalog only when all metadata is dependency-coherent."""

        report = self.validate(root)
        if not report.passed:
            raise PluginError(report.summary)
        return PluginCatalog(report.records, self._sdk_contract)

    def catalog_roots(
        self, roots: Iterable[PluginDiscoveryRoot]
    ) -> PluginCatalog:
        """Return one validated catalog across labeled discovery roots."""

        report = self.validate_roots(roots)
        if not report.passed:
            raise PluginError(report.summary)
        return PluginCatalog(report.records, self._sdk_contract)

    def _validate_inspection(
        self, inspection: PluginInspectionReport
    ) -> PluginValidationReport:
        if not inspection.passed:
            return PluginValidationReport(
                issues=inspection.issues,
            )

        compatible_records = []
        compatibility_issues = []
        for record in inspection.records:
            issue = self._sdk_contract.issue_for(record)
            if issue is None:
                compatible_records.append(record)
            else:
                compatibility_issues.append(issue)
        if compatibility_issues:
            return PluginValidationReport(
                records=tuple(compatible_records),
                issues=tuple(compatibility_issues),
            )

        catalog = PluginCatalog(inspection.records, self._sdk_contract)
        dependencies = self._dependency_resolver.resolve(catalog)
        return PluginValidationReport(
            records=inspection.records,
            dependency_resolutions=dependencies.resolutions,
            issues=dependencies.issues,
        )
