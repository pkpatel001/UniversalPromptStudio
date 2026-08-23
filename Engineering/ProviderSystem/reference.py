"""Built-in deterministic provider used for offline SDK integration."""

from __future__ import annotations

from .models import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderEntryPoint,
    ProviderId,
    ProviderManifest,
    ProviderMetadata,
    ProviderRecord,
    ProviderSdkVersion,
    ProviderTransport,
    ProviderVersion,
)
from .runtime_api import (
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTextResult,
    ProviderUsage,
)

OFFLINE_ECHO_PROVIDER_ID = ProviderId("ups.offline-echo")
OFFLINE_ECHO_PROVIDER_VERSION = ProviderVersion("1.0.0")


class OfflineEchoProvider:
    """Host-authored provider that performs deterministic local text generation."""

    @property
    def provider_id(self) -> ProviderId:
        return OFFLINE_ECHO_PROVIDER_ID

    @property
    def version(self) -> ProviderVersion:
        return OFFLINE_ECHO_PROVIDER_VERSION

    def generate_text(self, request: ProviderTextRequest) -> ProviderTextResult:
        """Return a deterministic response without filesystem or network access."""

        return ProviderTextResponse(
            request.request_id,
            f"[offline provider response]\n{request.prompt}",
            request.model,
            ProviderUsage(input_units=len(request.prompt), output_units=len(request.prompt)),
        )


def offline_echo_provider_record() -> ProviderRecord:
    """Return canonical host-owned metadata for the built-in offline provider."""

    return ProviderRecord(
        "offline-echo/ai-provider-manifest.yaml",
        ProviderManifest(
            1,
            ProviderMetadata(
                OFFLINE_ECHO_PROVIDER_ID,
                "UPS Offline Echo",
                OFFLINE_ECHO_PROVIDER_VERSION,
                ProviderSdkVersion(1),
                "Deterministic offline provider for application integration.",
                ProviderEntryPoint(
                    "Engineering.ProviderSystem.reference:OfflineEchoProvider"
                ),
                ProviderTransport.LOCAL,
                ProviderAuthentication.NONE,
            ),
            (ProviderCapability.TEXT_GENERATION,),
        ),
        root_id="builtin",
    )


__all__ = [
    "OFFLINE_ECHO_PROVIDER_ID",
    "OFFLINE_ECHO_PROVIDER_VERSION",
    "OfflineEchoProvider",
    "offline_echo_provider_record",
]
