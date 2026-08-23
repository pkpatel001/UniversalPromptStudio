"""Strict, non-executing schema-1 AI-provider manifest reader."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from Engineering.core.exceptions import EngineeringError, ProviderError
from Engineering.core.filesystem import read_yaml

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

AI_PROVIDER_MANIFEST_NAME = "ai-provider-manifest.yaml"
AI_PROVIDER_SCHEMA_VERSION = 1
AI_PROVIDER_SDK_API_LEVEL = 1

_ROOT_KEYS = frozenset({"schema_version", "provider"})
_PROVIDER_KEYS = frozenset(
    {
        "id",
        "name",
        "version",
        "sdk_version",
        "description",
        "entry_point",
        "transport",
        "authentication",
        "capabilities",
    }
)
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class ProviderManifestReader:
    """Parse provider metadata without importing code or contacting a service."""

    def detect_schema_version(self, path: Path) -> int:
        data = self._read(path)
        value = data.get("schema_version")
        if type(value) is not int:
            raise ProviderError("Provider manifest schema_version must be an integer.")
        return value

    def read(self, path: Path) -> ProviderManifest:
        return self._parse(self._read(path))

    def read_text(self, content: str) -> ProviderManifest:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ProviderError("Provider manifest YAML is malformed.") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ProviderError("Provider manifest could not be read: YAML root must be a mapping.")
        return self._parse(data)

    def _parse(self, data: dict[str, Any]) -> ProviderManifest:
        self._reject_secret_keys(data)
        self._require_exact_keys(data, _ROOT_KEYS, "Provider manifest")
        schema_version = data["schema_version"]
        if type(schema_version) is not int:
            raise ProviderError("Provider manifest schema_version must be an integer.")
        if schema_version != AI_PROVIDER_SCHEMA_VERSION:
            raise ProviderError(
                f"Unsupported provider manifest schema_version: {schema_version!r}."
            )
        provider = self._require_mapping(data["provider"], "provider")
        self._require_exact_keys(provider, _PROVIDER_KEYS, "provider")
        capabilities = self._read_capabilities(provider["capabilities"])
        return ProviderManifest(
            schema_version,
            ProviderMetadata(
                ProviderId(self._require_string(provider, "id")),
                self._require_string(provider, "name"),
                ProviderVersion(self._require_string(provider, "version")),
                ProviderSdkVersion(self._require_integer(provider, "sdk_version")),
                self._require_string(provider, "description"),
                ProviderEntryPoint(self._require_string(provider, "entry_point")),
                self._read_enum(
                    ProviderTransport,
                    provider["transport"],
                    "provider.transport",
                ),
                self._read_enum(
                    ProviderAuthentication,
                    provider["authentication"],
                    "provider.authentication",
                ),
            ),
            capabilities,
        )

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return read_yaml(path)
        except yaml.YAMLError as exc:
            raise ProviderError("Provider manifest YAML is malformed.") from exc
        except (EngineeringError, OSError, TypeError, UnicodeError) as exc:
            raise ProviderError(f"Provider manifest could not be read: {exc}") from exc

    @classmethod
    def _reject_secret_keys(cls, value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_text = str(key)
                path = f"{prefix}.{key_text}" if prefix else key_text
                normalized = key_text.lower().replace("-", "_")
                if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
                    raise ProviderError(
                        f"Secret-like provider manifest field is not allowed: {path}."
                    )
                cls._reject_secret_keys(nested, path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                cls._reject_secret_keys(nested, f"{prefix}[{index}]")

    @staticmethod
    def _require_exact_keys(data: dict[str, Any], expected: frozenset[str], label: str) -> None:
        if not all(isinstance(key, str) for key in data):
            raise ProviderError(f"{label} keys must be strings.")
        missing = sorted(expected - set(data))
        unexpected = sorted(set(data) - expected)
        if missing:
            raise ProviderError(f"{label} is missing keys: {', '.join(missing)}.")
        if unexpected:
            raise ProviderError(f"{label} contains unknown keys: {', '.join(unexpected)}.")

    @staticmethod
    def _require_mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ProviderError(f"{label} must be a mapping with string keys.")
        return value

    @staticmethod
    def _require_string(data: dict[str, Any], field: str) -> str:
        value = data[field]
        if not isinstance(value, str):
            raise ProviderError(f"provider.{field} must be a string.")
        return value

    @staticmethod
    def _require_integer(data: dict[str, Any], field: str) -> int:
        value = data[field]
        if type(value) is not int:
            raise ProviderError(f"provider.{field} must be an integer.")
        return value

    @staticmethod
    def _read_enum[T: StrEnum](enum_type: type[T], value: object, label: str) -> T:
        if not isinstance(value, str):
            raise ProviderError(f"{label} must be a string.")
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise ProviderError(f"{label} must be one of: {allowed}.") from exc

    @classmethod
    def _read_capabilities(cls, value: object) -> tuple[ProviderCapability, ...]:
        if not isinstance(value, list):
            raise ProviderError("provider.capabilities must be a list.")
        if not all(isinstance(item, str) for item in value):
            raise ProviderError("provider.capabilities entries must be strings.")
        if len(set(value)) != len(value):
            raise ProviderError("provider.capabilities contains duplicate entries.")
        return tuple(
            sorted(
                (
                    cls._read_enum(
                        ProviderCapability,
                        item,
                        "provider.capabilities entry",
                    )
                    for item in value
                ),
                key=lambda item: item.value,
            )
        )
