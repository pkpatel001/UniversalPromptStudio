"""Typed plugin metadata, packaging, and approval-gated runtime foundation."""

from .catalog import PluginCatalog
from .compatibility import PluginSdkContract
from .dependencies import PluginDependencyReport, PluginDependencyResolver
from .discovery import (
    DEFAULT_IGNORED_PLUGIN_DIRECTORIES,
    PluginDiscoveryService,
)
from .installation import PluginInstallationPlanner, PluginInstallPlan
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
from .package import (
    PLUGIN_PACKAGE_SUFFIX,
    PluginPackage,
    PluginPackageEntry,
    PluginPackageInspector,
    PluginTrustAssessment,
    PluginTrustPolicy,
    PluginTrustStatus,
)
from .runtime import (
    PluginLifecycleState,
    PluginRuntimeApproval,
    PluginRuntimeEvent,
    PluginRuntimeEventSink,
    PluginRuntimeManager,
    PluginRuntimeStatus,
)
from .runtime_api import (
    PluginContribution,
    PluginContributionRegistry,
    PluginRegistrationContext,
    RuntimePlugin,
)
from .runtime_loader import LoadedPlugin, PluginModuleLoader, TrustedInProcessLoader
from .runtime_snapshot import (
    PluginDirectorySnapshot,
    PluginDirectorySnapshotter,
    PluginSnapshotFile,
)
from .scaffold import (
    PLUGIN_SCAFFOLD_TEMPLATE_ID,
    PLUGIN_SCAFFOLD_TEMPLATE_VERSION,
    PluginScaffoldRequest,
    PluginScaffoldResult,
    PluginScaffoldService,
)
from .service import PluginService

__all__ = [
    "DEFAULT_IGNORED_PLUGIN_DIRECTORIES",
    "PLUGIN_MANIFEST_NAME",
    "PLUGIN_PACKAGE_SUFFIX",
    "PLUGIN_SCHEMA_VERSION",
    "PLUGIN_SDK_API_LEVEL",
    "PLUGIN_SCAFFOLD_TEMPLATE_ID",
    "PLUGIN_SCAFFOLD_TEMPLATE_VERSION",
    "PluginCapability",
    "PluginCatalog",
    "PluginDependency",
    "PluginDependencyReport",
    "PluginDependencyResolution",
    "PluginDependencyResolver",
    "PluginDirectorySnapshot",
    "PluginDirectorySnapshotter",
    "PluginDiscoveryRoot",
    "PluginDiscoveryService",
    "PluginEntryPoint",
    "PluginId",
    "PluginInspectionReport",
    "PluginInstallPlan",
    "PluginInstallationPlanner",
    "PluginIssue",
    "PluginLifecycleState",
    "PluginContribution",
    "PluginContributionRegistry",
    "PluginRegistrationContext",
    "PluginManifest",
    "PluginManifestReader",
    "PluginMetadata",
    "PluginPackage",
    "PluginPackageEntry",
    "PluginPackageInspector",
    "PluginModuleLoader",
    "PluginPermission",
    "PluginRecord",
    "PluginSdkVersion",
    "PluginSdkCompatibility",
    "PluginSdkContract",
    "PluginScaffoldRequest",
    "PluginScaffoldResult",
    "PluginScaffoldService",
    "PluginRuntimeApproval",
    "PluginRuntimeEvent",
    "PluginRuntimeEventSink",
    "PluginRuntimeManager",
    "PluginRuntimeStatus",
    "PluginSnapshotFile",
    "PluginService",
    "PluginTrustAssessment",
    "PluginTrustPolicy",
    "PluginTrustStatus",
    "PluginValidationReport",
    "PluginVersion",
    "LoadedPlugin",
    "RuntimePlugin",
    "TrustedInProcessLoader",
]
