"""E-013 typed, deterministic, non-executing plugin metadata foundation."""

from .catalog import PluginCatalog
from .compatibility import PluginSdkContract
from .dependencies import PluginDependencyReport, PluginDependencyResolver
from .discovery import (
    DEFAULT_IGNORED_PLUGIN_DIRECTORIES,
    PluginDiscoveryService,
)
from .manifest import (
    PLUGIN_MANIFEST_NAME,
    PLUGIN_SCHEMA_VERSION,
    PLUGIN_SDK_API_LEVEL,
    PluginManifestReader,
)
from .models import (
    PluginCapability,
    PluginDependency,
    PluginDependencyResolution,
    PluginDiscoveryRoot,
    PluginEntryPoint,
    PluginId,
    PluginInspectionReport,
    PluginIssue,
    PluginManifest,
    PluginMetadata,
    PluginPermission,
    PluginRecord,
    PluginSdkCompatibility,
    PluginSdkVersion,
    PluginValidationReport,
    PluginVersion,
)
from .service import PluginService

__all__ = [
    "DEFAULT_IGNORED_PLUGIN_DIRECTORIES",
    "PLUGIN_MANIFEST_NAME",
    "PLUGIN_SCHEMA_VERSION",
    "PLUGIN_SDK_API_LEVEL",
    "PluginCapability",
    "PluginCatalog",
    "PluginDependency",
    "PluginDependencyReport",
    "PluginDependencyResolution",
    "PluginDependencyResolver",
    "PluginDiscoveryRoot",
    "PluginDiscoveryService",
    "PluginEntryPoint",
    "PluginId",
    "PluginInspectionReport",
    "PluginIssue",
    "PluginManifest",
    "PluginManifestReader",
    "PluginMetadata",
    "PluginPermission",
    "PluginRecord",
    "PluginSdkVersion",
    "PluginSdkCompatibility",
    "PluginSdkContract",
    "PluginService",
    "PluginValidationReport",
    "PluginVersion",
]
