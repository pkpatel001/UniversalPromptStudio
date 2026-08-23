"""E-014 AI-provider SDK metadata and manifest foundation."""

from .catalog import ProviderCatalog
from .compatibility import ProviderSdkContract
from .discovery import (
    DEFAULT_IGNORED_PROVIDER_DIRECTORIES,
    ProviderDiscoveryService,
)
from .execution import ProviderExecutionReport, ProviderExecutionService
from .manifest import (
    AI_PROVIDER_MANIFEST_NAME,
    AI_PROVIDER_SCHEMA_VERSION,
    AI_PROVIDER_SDK_API_LEVEL,
    ProviderManifestReader,
)
from .models import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderDiscoveryRoot,
    ProviderEntryPoint,
    ProviderId,
    ProviderInspectionReport,
    ProviderIssue,
    ProviderManifest,
    ProviderMetadata,
    ProviderRecord,
    ProviderSdkCompatibility,
    ProviderSdkVersion,
    ProviderTransport,
    ProviderValidationReport,
    ProviderVersion,
)
from .reference import (
    OFFLINE_ECHO_PROVIDER_ID,
    OFFLINE_ECHO_PROVIDER_VERSION,
    OfflineEchoProvider,
    offline_echo_provider_record,
)
from .runtime_api import (
    ProviderFailure,
    ProviderFailureCode,
    ProviderOptionValue,
    ProviderRequestOption,
    ProviderRuntimeRegistration,
    ProviderRuntimeRegistry,
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTextResult,
    ProviderUsage,
    RuntimeTextProvider,
)
from .scaffold import (
    PROVIDER_SCAFFOLD_TEMPLATE_ID,
    PROVIDER_SCAFFOLD_TEMPLATE_VERSION,
    ProviderScaffoldRequest,
    ProviderScaffoldResult,
    ProviderScaffoldService,
)
from .service import ProviderService

__all__ = [
    "AI_PROVIDER_MANIFEST_NAME",
    "AI_PROVIDER_SCHEMA_VERSION",
    "AI_PROVIDER_SDK_API_LEVEL",
    "PROVIDER_SCAFFOLD_TEMPLATE_ID",
    "PROVIDER_SCAFFOLD_TEMPLATE_VERSION",
    "DEFAULT_IGNORED_PROVIDER_DIRECTORIES",
    "OFFLINE_ECHO_PROVIDER_ID",
    "OFFLINE_ECHO_PROVIDER_VERSION",
    "OfflineEchoProvider",
    "ProviderAuthentication",
    "ProviderCapability",
    "ProviderCatalog",
    "ProviderDiscoveryRoot",
    "ProviderDiscoveryService",
    "ProviderEntryPoint",
    "ProviderExecutionReport",
    "ProviderExecutionService",
    "ProviderFailure",
    "ProviderFailureCode",
    "ProviderId",
    "ProviderManifest",
    "ProviderManifestReader",
    "ProviderMetadata",
    "ProviderInspectionReport",
    "ProviderIssue",
    "ProviderRecord",
    "ProviderOptionValue",
    "ProviderRequestOption",
    "ProviderRuntimeRegistration",
    "ProviderRuntimeRegistry",
    "ProviderSdkCompatibility",
    "ProviderSdkContract",
    "ProviderSdkVersion",
    "ProviderScaffoldRequest",
    "ProviderScaffoldResult",
    "ProviderScaffoldService",
    "ProviderService",
    "ProviderTransport",
    "ProviderTextRequest",
    "ProviderTextResponse",
    "ProviderTextResult",
    "ProviderUsage",
    "ProviderValidationReport",
    "ProviderVersion",
    "RuntimeTextProvider",
    "offline_echo_provider_record",
]
