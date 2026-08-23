"""E-014 AI-provider SDK metadata and manifest foundation."""

from .manifest import (
    AI_PROVIDER_MANIFEST_NAME,
    AI_PROVIDER_SCHEMA_VERSION,
    AI_PROVIDER_SDK_API_LEVEL,
    ProviderManifestReader,
)
from .models import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderEntryPoint,
    ProviderId,
    ProviderManifest,
    ProviderMetadata,
    ProviderSdkVersion,
    ProviderTransport,
    ProviderVersion,
)

__all__ = [
    "AI_PROVIDER_MANIFEST_NAME",
    "AI_PROVIDER_SCHEMA_VERSION",
    "AI_PROVIDER_SDK_API_LEVEL",
    "ProviderAuthentication",
    "ProviderCapability",
    "ProviderEntryPoint",
    "ProviderId",
    "ProviderManifest",
    "ProviderManifestReader",
    "ProviderMetadata",
    "ProviderSdkVersion",
    "ProviderTransport",
    "ProviderVersion",
]
