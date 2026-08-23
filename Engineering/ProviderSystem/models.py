"""Immutable E-014.1 AI-provider SDK metadata models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packaging.version import InvalidVersion, Version

from Engineering.core.exceptions import ProviderError

from .validation import require_entry_point, require_nonempty_text, require_provider_id


@dataclass(frozen=True, slots=True)
class ProviderId:
    """Stable vendor-qualified AI-provider identity."""

    value: str

    def __post_init__(self) -> None:
        require_provider_id(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ProviderVersion:
    """Canonical PEP 440 version for one provider implementation."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise ProviderError(
                "Provider version must be a non-empty value of at most 64 characters."
            )
        try:
            parsed = Version(self.value)
        except InvalidVersion as exc:
            raise ProviderError(f"Invalid provider version: {self.value!r}") from exc
        if (
            str(parsed) != self.value
            or len(parsed.release) != 3
            or parsed.epoch != 0
            or parsed.local is not None
        ):
            raise ProviderError(
                "Provider version must use canonical PEP 440 form with exactly "
                "major.minor.patch release components and no epoch or local version."
            )

    @property
    def parsed(self) -> Version:
        return Version(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ProviderSdkVersion:
    """Positive UPS AI Provider SDK API level."""

    api_level: int

    def __post_init__(self) -> None:
        if type(self.api_level) is not int or self.api_level < 1:
            raise ProviderError("Provider sdk_version must be a positive integer API level.")


@dataclass(frozen=True, slots=True)
class ProviderEntryPoint:
    """Unresolved Python entry-point metadata."""

    value: str

    def __post_init__(self) -> None:
        require_entry_point(self.value)

    def __str__(self) -> str:
        return self.value


class ProviderCapability(StrEnum):
    """Host-recognized behavior categories declared by an AI provider."""

    TEXT_GENERATION = "text-generation"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    IMAGE_GENERATION = "image-generation"
    AUDIO_INPUT = "audio-input"
    AUDIO_OUTPUT = "audio-output"
    TOOL_CALLING = "tool-calling"


class ProviderTransport(StrEnum):
    """How a future runtime implementation reaches its model service."""

    LOCAL = "local"
    HTTP = "http"


class ProviderAuthentication(StrEnum):
    """Authentication shape only; no credential names or values are stored."""

    NONE = "none"
    API_KEY = "api-key"
    OAUTH2 = "oauth2"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Identity and descriptive metadata for one provider implementation."""

    provider_id: ProviderId
    name: str
    version: ProviderVersion
    sdk_version: ProviderSdkVersion
    description: str
    entry_point: ProviderEntryPoint
    transport: ProviderTransport
    authentication: ProviderAuthentication

    def __post_init__(self) -> None:
        require_nonempty_text(self.name, "Provider name", maximum=120)
        require_nonempty_text(self.description, "Provider description", maximum=1000)


@dataclass(frozen=True, slots=True)
class ProviderManifest:
    """Canonical schema-1 AI-provider metadata document."""

    schema_version: int
    metadata: ProviderMetadata
    capabilities: tuple[ProviderCapability, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ProviderError("Provider manifest schema_version must be integer 1.")
        if not self.capabilities:
            raise ProviderError("Provider manifest must declare at least one capability.")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ProviderError("Provider manifest capabilities must be unique.")
