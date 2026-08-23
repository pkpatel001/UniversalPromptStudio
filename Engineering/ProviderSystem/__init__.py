"""E-014 AI-provider SDK metadata and manifest foundation."""

from .catalog import ProviderCatalog
from .compatibility import ProviderSdkContract
from .discovery import (
    DEFAULT_IGNORED_PROVIDER_DIRECTORIES,
    ProviderDiscoveryService,
)
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
    ProviderManifest,
    ProviderMetadata,
    ProviderInspectionReport,
    ProviderIssue,
    ProviderRecord,
    ProviderSdkCompatibility,
    ProviderSdkVersion,
    ProviderTransport,
    ProviderValidationReport,
    ProviderVersion,
)
from .service import ProviderService

__all__ = [
    "AI_PROVIDER_MANIFEST_NAME",
    "AI_PROVIDER_SCHEMA_VERSION",
    "AI_PROVIDER_SDK_API_LEVEL",
    "DEFAULT_IGNORED_PROVIDER_DIRECTORIES",
    "ProviderAuthentication",
    "ProviderCapability",
    "ProviderCatalog",
    "ProviderDiscoveryRoot",
    "ProviderDiscoveryService",
    "ProviderEntryPoint",
    "ProviderId",
    "ProviderManifest",
    "ProviderManifestReader",
    "ProviderMetadata",
    "ProviderInspectionReport",
    "ProviderIssue",
    "ProviderRecord",
    "ProviderSdkCompatibility",
    "ProviderSdkContract",
    "ProviderSdkVersion",
    "ProviderService",
    "ProviderTransport",
    "ProviderValidationReport",
    "ProviderVersion",
]
