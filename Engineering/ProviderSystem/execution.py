"""Controlled invocation of explicitly registered AI-provider instances."""

from __future__ import annotations

from dataclasses import dataclass

from Engineering.core.exceptions import ProviderError

from .models import ProviderId, ProviderVersion
from .runtime_api import (
    ProviderFailure,
    ProviderFailureCode,
    ProviderRuntimeRegistration,
    ProviderRuntimeRegistry,
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTextResult,
)


@dataclass(frozen=True, slots=True)
class ProviderExecutionReport:
    """One correlated outcome from one exact registered provider version."""

    provider_id: ProviderId
    version: ProviderVersion
    result: ProviderTextResult

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, ProviderId):
            raise ProviderError("Execution report provider_id must be ProviderId.")
        if not isinstance(self.version, ProviderVersion):
            raise ProviderError("Execution report version must be ProviderVersion.")
        if not isinstance(self.result, ProviderTextResponse | ProviderFailure):
            raise ProviderError("Execution report result must be a provider text result.")

    @property
    def succeeded(self) -> bool:
        """Return whether the provider produced a successful text response."""

        return isinstance(self.result, ProviderTextResponse)


class ProviderExecutionService:
    """Invoke one explicitly registered provider once and contain its failures."""

    def __init__(self, registry: ProviderRuntimeRegistry) -> None:
        if not isinstance(registry, ProviderRuntimeRegistry):
            raise ProviderError("Provider execution requires ProviderRuntimeRegistry.")
        self._registry = registry

    def execute(
        self,
        provider_id: str,
        request: ProviderTextRequest,
        version: str | None = None,
    ) -> ProviderExecutionReport:
        """Resolve and invoke one provider without loading, retrying, or configuring it."""

        if not isinstance(request, ProviderTextRequest):
            raise ProviderError("Provider execution request must be ProviderTextRequest.")
        registration = self._registry.resolve(provider_id, version)
        identity_failure = self._identity_failure(registration, request.request_id)
        if identity_failure is not None:
            return self._report(registration, identity_failure)

        try:
            result = registration.implementation.generate_text(request)
        except Exception:
            result = ProviderFailure(
                request.request_id,
                ProviderFailureCode.PROVIDER_ERROR,
                "Provider execution failed.",
            )
        result = self._validated_result(request, result)
        return self._report(registration, result)

    @staticmethod
    def _identity_failure(
        registration: ProviderRuntimeRegistration,
        request_id: str,
    ) -> ProviderFailure | None:
        try:
            identity_matches = (
                registration.implementation.provider_id
                == registration.record.manifest.metadata.provider_id
                and registration.implementation.version
                == registration.record.manifest.metadata.version
            )
        except Exception:
            identity_matches = False
        if identity_matches:
            return None
        return ProviderFailure(
            request_id,
            ProviderFailureCode.PROVIDER_ERROR,
            "Provider runtime identity changed after registration.",
        )

    @staticmethod
    def _validated_result(
        request: ProviderTextRequest,
        result: object,
    ) -> ProviderTextResult:
        if not isinstance(result, ProviderTextResponse | ProviderFailure):
            return ProviderFailure(
                request.request_id,
                ProviderFailureCode.PROVIDER_ERROR,
                "Provider returned an invalid result.",
            )
        if result.request_id != request.request_id:
            return ProviderFailure(
                request.request_id,
                ProviderFailureCode.PROVIDER_ERROR,
                "Provider returned a result for a different request.",
            )
        return result

    @staticmethod
    def _report(
        registration: ProviderRuntimeRegistration,
        result: ProviderTextResult,
    ) -> ProviderExecutionReport:
        return ProviderExecutionReport(
            registration.record.manifest.metadata.provider_id,
            registration.record.manifest.metadata.version,
            result,
        )


__all__ = ["ProviderExecutionReport", "ProviderExecutionService"]
