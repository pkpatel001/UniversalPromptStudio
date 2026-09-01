"""Controlled A-004 provider settings and credential references."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

OPENAI_RESPONSES_PROVIDER = "ups.openai-responses"
OPENAI_RESPONSES_VERSION = "1.0.0"
OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
OPENAI_CREDENTIAL_REFERENCE = "provider:ups.openai-responses:default"
PROVIDER_SETTINGS_FILE_NAME = "provider-settings.json"
MAX_MODEL_LENGTH = 80
MAX_CREDENTIAL_LENGTH = 512
MAX_OUTPUT_TOKENS = 4_096
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


class ProviderUnavailableError(RuntimeError):
    """Provider configuration or credential state is unavailable."""


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """Non-secret settings for the single configurable provider."""

    provider_id: str = OPENAI_RESPONSES_PROVIDER
    endpoint: str = OPENAI_RESPONSES_ENDPOINT
    model: str = "gpt-5-mini"
    temperature: float = 1.0
    max_output_tokens: int = 1_024
    credential_reference: str = OPENAI_CREDENTIAL_REFERENCE

    def __post_init__(self) -> None:
        if self.provider_id != OPENAI_RESPONSES_PROVIDER:
            raise ValueError("Provider identity is not host-authorized.")
        if self.endpoint != OPENAI_RESPONSES_ENDPOINT:
            raise ValueError("Provider endpoint is not host-authorized.")
        if not isinstance(self.model, str) or not _MODEL_PATTERN.fullmatch(self.model):
            raise ValueError("Provider model is invalid.")
        if isinstance(self.temperature, bool) or not isinstance(self.temperature, int | float):
            raise ValueError("Provider temperature is invalid.")
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise ValueError("Provider temperature is invalid.")
        if (
            type(self.max_output_tokens) is not int
            or not 1 <= self.max_output_tokens <= MAX_OUTPUT_TOKENS
        ):
            raise ValueError("Provider output-token limit is invalid.")
        if self.credential_reference != OPENAI_CREDENTIAL_REFERENCE:
            raise ValueError("Provider credential reference is invalid.")


class ProviderSettingsRepository(Protocol):
    """Persist non-secret provider settings."""

    def get(self) -> ProviderSettings | None: ...

    def save(self, settings: ProviderSettings) -> None: ...


class SecretStore(Protocol):
    """Resolve opaque credential references without exposing storage details."""

    def set(self, reference: str, secret: str) -> None: ...

    def get(self, reference: str) -> str | None: ...

    def delete(self, reference: str) -> bool: ...

    def contains(self, reference: str) -> bool: ...


class InMemoryProviderSettingsRepository:
    """Test and ephemeral-host settings repository."""

    def __init__(self) -> None:
        self._settings: ProviderSettings | None = None

    def get(self) -> ProviderSettings | None:
        return self._settings

    def save(self, settings: ProviderSettings) -> None:
        self._settings = settings


class JsonProviderSettingsRepository:
    """Atomic exact-shape non-secret settings below application data."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("Provider settings path must be absolute.")
        self._path = path

    def get(self) -> ProviderSettings | None:
        if not self._path.exists():
            return None
        try:
            raw = self._path.read_bytes()
            if len(raw) > 4_096:
                raise ValueError("Provider settings are invalid.")
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Provider settings are invalid.") from exc
        if not isinstance(value, dict) or set(value) != {"schema_version", "settings"}:
            raise ValueError("Provider settings are invalid.")
        if value["schema_version"] != 1 or not isinstance(value["settings"], dict):
            raise ValueError("Provider settings are invalid.")
        expected = set(asdict(ProviderSettings()))
        if set(value["settings"]) != expected:
            raise ValueError("Provider settings are invalid.")
        return ProviderSettings(**value["settings"])

    def save(self, settings: ProviderSettings) -> None:
        payload = json.dumps(
            {"schema_version": 1, "settings": asdict(settings)},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".provider-settings-", suffix=".tmp", dir=self._path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise


class InMemorySecretStore:
    """Secret-store test double that never serializes values."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def set(self, reference: str, secret: str) -> None:
        _validate_reference(reference)
        _validate_secret(secret)
        self._values[reference] = secret

    def get(self, reference: str) -> str | None:
        _validate_reference(reference)
        return self._values.get(reference)

    def delete(self, reference: str) -> bool:
        _validate_reference(reference)
        return self._values.pop(reference, None) is not None

    def contains(self, reference: str) -> bool:
        _validate_reference(reference)
        return reference in self._values


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    """Safe public view of one host-authorized provider."""

    provider_id: str
    name: str
    version: str
    transport: str
    authentication: str
    configurable: bool
    available: bool
    credential_state: str
    credential_reference: str | None
    endpoint: str | None
    model: str | None
    temperature: float | None
    max_output_tokens: int | None


class ProviderConfigurationService:
    """Own settings validation and opaque credential lifecycle."""

    def __init__(
        self,
        repository: ProviderSettingsRepository,
        secret_store: SecretStore,
    ) -> None:
        self._repository = repository
        self._secret_store = secret_store

    def catalog(self) -> tuple[ProviderStatus, ProviderStatus]:
        settings = self._repository.get()
        credential_available = self._secret_store.contains(OPENAI_CREDENTIAL_REFERENCE)
        configured = settings is not None
        public_settings = settings or ProviderSettings()
        return (
            ProviderStatus(
                "ups.offline-echo",
                "UPS Offline Echo",
                "1.0.0",
                "local",
                "none",
                False,
                True,
                "not-required",
                None,
                None,
                None,
                None,
                None,
            ),
            ProviderStatus(
                OPENAI_RESPONSES_PROVIDER,
                "OpenAI Responses",
                OPENAI_RESPONSES_VERSION,
                "https",
                "api-key",
                True,
                configured and credential_available,
                "stored" if credential_available else "missing",
                OPENAI_CREDENTIAL_REFERENCE,
                public_settings.endpoint,
                public_settings.model,
                float(public_settings.temperature),
                public_settings.max_output_tokens,
            ),
        )

    def save(
        self,
        provider_id: str,
        endpoint: str,
        model: str,
        temperature: float,
        max_output_tokens: int,
        credential: str | None,
    ) -> ProviderStatus:
        settings = ProviderSettings(
            provider_id,
            endpoint,
            model,
            temperature,
            max_output_tokens,
        )
        if credential is not None:
            _validate_secret(credential)
            previous = self._secret_store.get(settings.credential_reference)
            self._secret_store.set(settings.credential_reference, credential)
            try:
                self._repository.save(settings)
            except Exception:
                if previous is None:
                    self._secret_store.delete(settings.credential_reference)
                else:
                    self._secret_store.set(settings.credential_reference, previous)
                raise
        else:
            self._repository.save(settings)
        return self.catalog()[1]

    def clear_credential(self, provider_id: str) -> ProviderStatus:
        if provider_id != OPENAI_RESPONSES_PROVIDER:
            raise ValueError("Provider identity is not configurable.")
        self._secret_store.delete(OPENAI_CREDENTIAL_REFERENCE)
        return self.catalog()[1]

    def require_execution_settings(self, provider_id: str) -> ProviderSettings:
        if provider_id != OPENAI_RESPONSES_PROVIDER:
            raise ValueError("Provider identity is not executable by this command.")
        settings = self._repository.get()
        if settings is None or not self._secret_store.contains(settings.credential_reference):
            raise ProviderUnavailableError("Configured provider is unavailable.")
        return settings

    def credential(self, reference: str) -> str | None:
        return self._secret_store.get(reference)


def _validate_reference(reference: str) -> None:
    if reference != OPENAI_CREDENTIAL_REFERENCE:
        raise ValueError("Credential reference is invalid.")


def _validate_secret(secret: str) -> None:
    if (
        not isinstance(secret, str)
        or not 8 <= len(secret) <= MAX_CREDENTIAL_LENGTH
        or secret != secret.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in secret)
    ):
        raise ValueError("Credential value is invalid.")


__all__ = [
    "InMemoryProviderSettingsRepository",
    "InMemorySecretStore",
    "JsonProviderSettingsRepository",
    "MAX_CREDENTIAL_LENGTH",
    "MAX_MODEL_LENGTH",
    "MAX_OUTPUT_TOKENS",
    "OPENAI_CREDENTIAL_REFERENCE",
    "OPENAI_RESPONSES_ENDPOINT",
    "OPENAI_RESPONSES_PROVIDER",
    "OPENAI_RESPONSES_VERSION",
    "PROVIDER_SETTINGS_FILE_NAME",
    "ProviderConfigurationService",
    "ProviderSettings",
    "ProviderStatus",
    "ProviderUnavailableError",
    "SecretStore",
]
