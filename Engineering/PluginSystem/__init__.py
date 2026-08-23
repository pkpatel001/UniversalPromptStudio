"""E-013.1 typed, deterministic, non-executing plugin metadata foundation."""

from .catalog import PluginCatalog
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
    PluginEntryPoint,
    PluginId,
    PluginInspectionReport,
    PluginIssue,
    PluginManifest,
    PluginMetadata,
    PluginPermission,
    PluginRecord,
    PluginSdkVersion,
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
    "PluginService",
    "PluginVersion",
]
