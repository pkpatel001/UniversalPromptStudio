"""Read-only application service for plugin inspection and cataloging."""

from __future__ import annotations

from pathlib import Path

from Engineering.core.exceptions import PluginError

from .catalog import PluginCatalog
from .discovery import PluginDiscoveryService
from .models import PluginInspectionReport


class PluginService:
    """Compose plugin discovery and deterministic catalog construction."""

    def __init__(self, discovery: PluginDiscoveryService | None = None) -> None:
        self._discovery = discovery or PluginDiscoveryService()

    def inspect(self, root: Path) -> PluginInspectionReport:
        """Return all valid records and deterministic issues below root."""

        return self._discovery.inspect(root)

    def catalog(self, root: Path) -> PluginCatalog:
        """Return a catalog only when discovery is completely valid."""

        report = self.inspect(root)
        if not report.passed:
            raise PluginError(report.summary)
        return PluginCatalog(report.records)
