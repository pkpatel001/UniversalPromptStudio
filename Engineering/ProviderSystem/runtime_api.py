"""Typed, non-executing AI-provider runtime contracts and registration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from Engineering.core.exceptions import ProviderError

from .compatibility import ProviderSdkContract
from .models import ProviderCapability, ProviderId, ProviderRecord, ProviderVersion
from .validation import require_metadata_id, require_nonempty_text

type ProviderOptionValue = str | int | float | bool

_SECRET_KEY_PHRASES = (
    "access-key",
    "api-key",
    "private-key",
)
_SECRET_KEY_SEGMENTS = frozenset(
    {
        "auth",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class ProviderRequestOption:
    """One portable, non-secret text-generation request option."""

    name: str
    value: ProviderOptionValue

    def __post_init__(self) -> None:
        require_metadata_id(self.name, "Provider request option")
        normalized = self.name.replace(".", "-")
        segments = frozenset(normalized.split("-"))
        if segments.intersection(_SECRET_KEY_SEGMENTS) or any(
            normalized == phrase or normalized.endswith(f"-{phrase}")
            for phrase in _SECRET_KEY_PHRASES
        ):
            raise ProviderError(
                f"Provider request option must not carry credential material: {self.name!r}."
            )
        if not isinstance(self.value, str | int | float | bool):
            raise ProviderError("Provider request option value must be a scalar value.")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ProviderError("Provider request option float value must be finite.")


@dataclass(frozen=True, slots=True)
class ProviderTextRequest:
    """Host-neutral request contract for one future text-generation call."""

    request_id: str
    prompt: str
    model: str | None = None
    options: tuple[ProviderRequestOption, ...] = ()

    def __post_init__(self) -> None:
        require_nonempty_text(self.request_id, "Provider request id", maximum=128)
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ProviderError("Provider prompt must contain non-whitespace text.")
        if self.model is not None:
            require_nonempty_text(self.model, "Provider model", maximum=256)
        if not isinstance(self.options, tuple) or not all(
            isinstance(item, ProviderRequestOption) for item in self.options
        ):
            raise ProviderError("Provider request options must be a tuple of options.")
        names = tuple(item.name for item in self.options)
        if len(set(names)) != len(names):
            raise ProviderError("Provider request option names must be unique.")


@dataclass(frozen=True, slots=True)
class ProviderUsage:
    """Optional provider-reported text-unit usage."""

    input_units: int = 0
    output_units: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.input_units) is not int
            or self.input_units < 0
            or type(self.output_units) is not int
            or self.output_units < 0
        ):
            raise ProviderError("Provider usage values must be non-negative integers.")


@dataclass(frozen=True, slots=True)
class ProviderTextResponse:
    """Successful result for one text-generation request."""

    request_id: str
    text: str
    model: str | None = None
    usage: ProviderUsage = ProviderUsage()

    def __post_init__(self) -> None:
        require_nonempty_text(self.request_id, "Provider response request id", maximum=128)
        if not isinstance(self.text, str):
            raise ProviderError("Provider response text must be a string.")
        if self.model is not None:
            require_nonempty_text(self.model, "Provider response model", maximum=256)
        if not isinstance(self.usage, ProviderUsage):
            raise ProviderError("Provider response usage must be ProviderUsage.")


class ProviderFailureCode(StrEnum):
    """Stable, transport-neutral categories for provider failures."""

    INVALID_REQUEST = "invalid-request"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    RATE_LIMITED = "rate-limited"
    SERVICE_UNAVAILABLE = "service-unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PROVIDER_ERROR = "provider-error"


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    """Structured failure returned instead of leaking provider exceptions."""

    request_id: str
    code: ProviderFailureCode
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        require_nonempty_text(self.request_id, "Provider failure request id", maximum=128)
        if not isinstance(self.code, ProviderFailureCode):
            raise ProviderError("Provider failure code must be ProviderFailureCode.")
        require_nonempty_text(self.message, "Provider failure message", maximum=1000)
        if type(self.retryable) is not bool:
            raise ProviderError("Provider failure retryable must be a boolean.")


type ProviderTextResult = ProviderTextResponse | ProviderFailure


@runtime_checkable
class RuntimeTextProvider(Protocol):
    """Structural contract for a host-supplied text provider instance."""

    @property
    def provider_id(self) -> ProviderId:
        """Return the exact stable provider identity implemented by this instance."""

    @property
    def version(self) -> ProviderVersion:
        """Return the exact implementation version provided by this instance."""

    def generate_text(self, request: ProviderTextRequest) -> ProviderTextResult:
        """Generate text when a later execution host explicitly invokes the provider."""


@dataclass(frozen=True, slots=True)
class ProviderRuntimeRegistration:
    """One validated metadata-to-runtime binding supplied by the host."""

    record: ProviderRecord
    implementation: RuntimeTextProvider

    @property
    def provider_id(self) -> str:
        return self.record.provider_id

    @property
    def version(self) -> str:
        return self.record.version


class ProviderRuntimeRegistry:
    """Explicitly bind already-created providers without loading or executing code."""

    def __init__(self, sdk_contract: ProviderSdkContract | None = None) -> None:
        self._sdk_contract = sdk_contract or ProviderSdkContract()
        self._registrations: dict[tuple[str, str], ProviderRuntimeRegistration] = {}

    def register(self, record: ProviderRecord, implementation: RuntimeTextProvider) -> None:
        """Register one compatible text provider without importing or invoking it."""

        issue = self._sdk_contract.issue_for(record)
        if issue is not None:
            raise ProviderError(issue.message)
        if ProviderCapability.TEXT_GENERATION not in record.manifest.capabilities:
            raise ProviderError(
                f"Provider {record.provider_id} version {record.version} did not declare "
                "the text-generation capability."
            )
        if not isinstance(implementation, RuntimeTextProvider):
            raise ProviderError("Provider runtime does not implement RuntimeTextProvider.")
        if implementation.provider_id != record.manifest.metadata.provider_id:
            raise ProviderError("Provider runtime id does not match its manifest record.")
        if implementation.version != record.manifest.metadata.version:
            raise ProviderError("Provider runtime version does not match its manifest record.")
        key = (record.provider_id, record.version)
        if key in self._registrations:
            raise ProviderError(
                f"Provider runtime is already registered: {record.provider_id} "
                f"version {record.version}."
            )
        self._registrations[key] = ProviderRuntimeRegistration(record, implementation)

    def unregister(self, provider_id: str, version: str) -> ProviderRuntimeRegistration:
        """Remove one exact binding; missing identities are explicit errors."""

        ProviderId(provider_id)
        ProviderVersion(version)
        try:
            return self._registrations.pop((provider_id, version))
        except KeyError as exc:
            raise ProviderError(
                f"Provider runtime is not registered: {provider_id} version {version}."
            ) from exc

    def resolve(
        self,
        provider_id: str,
        version: str | None = None,
    ) -> ProviderRuntimeRegistration:
        """Resolve an exact or highest registered text-provider version."""

        ProviderId(provider_id)
        if version is not None:
            ProviderVersion(version)
        candidates = tuple(
            registration
            for (registered_id, registered_version), registration in self._registrations.items()
            if registered_id == provider_id
            and (version is None or registered_version == version)
        )
        if not candidates:
            suffix = f" version {version}" if version is not None else ""
            raise ProviderError(f"Provider runtime is not registered: {provider_id}{suffix}.")
        return max(
            candidates,
            key=lambda item: item.record.manifest.metadata.version.parsed,
        )

    @property
    def registrations(self) -> tuple[ProviderRuntimeRegistration, ...]:
        """Return registered bindings in deterministic identity/version order."""

        return tuple(
            sorted(
                self._registrations.values(),
                key=lambda item: (
                    item.provider_id,
                    item.record.manifest.metadata.version.parsed,
                ),
            )
        )


__all__ = [
    "ProviderFailure",
    "ProviderFailureCode",
    "ProviderOptionValue",
    "ProviderRequestOption",
    "ProviderRuntimeRegistration",
    "ProviderRuntimeRegistry",
    "ProviderTextRequest",
    "ProviderTextResponse",
    "ProviderTextResult",
    "ProviderUsage",
    "RuntimeTextProvider",
]
