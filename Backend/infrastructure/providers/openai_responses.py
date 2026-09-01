"""Host-authored bounded OpenAI Responses provider for A-004."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from Backend.application.provider_settings import (
    OPENAI_RESPONSES_PROVIDER,
    OPENAI_RESPONSES_VERSION,
    ProviderConfigurationService,
)
from Engineering.ProviderSystem import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderEntryPoint,
    ProviderFailure,
    ProviderFailureCode,
    ProviderId,
    ProviderManifest,
    ProviderMetadata,
    ProviderRecord,
    ProviderSdkVersion,
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTextResult,
    ProviderTransport,
    ProviderUsage,
    ProviderVersion,
)

type JsonObject = dict[str, object]
type HttpTransport = Callable[[str, str, JsonObject], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class _SafeTransportError(Exception):
    code: ProviderFailureCode
    retryable: bool = False


class OpenAIResponsesProvider:
    """Invoke one fixed HTTPS API using host-owned configuration and credentials."""

    def __init__(
        self,
        configuration: ProviderConfigurationService,
        transport: HttpTransport | None = None,
    ) -> None:
        self._configuration = configuration
        self._transport = transport or _post_json

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId(OPENAI_RESPONSES_PROVIDER)

    @property
    def version(self) -> ProviderVersion:
        return ProviderVersion(OPENAI_RESPONSES_VERSION)

    def generate_text(self, request: ProviderTextRequest) -> ProviderTextResult:
        try:
            settings = self._configuration.require_execution_settings(OPENAI_RESPONSES_PROVIDER)
            credential = self._configuration.credential(settings.credential_reference)
            options = {item.name: item.value for item in request.options}
            if (
                request.model != settings.model
                or set(options) != {"temperature", "max-output-tokens"}
                or options["temperature"] != settings.temperature
                or options["max-output-tokens"] != settings.max_output_tokens
                or credential is None
            ):
                return _failure(request, ProviderFailureCode.CONFIGURATION)
            response = self._transport(
                settings.endpoint,
                credential,
                {
                    "input": request.prompt,
                    "model": settings.model,
                    "temperature": settings.temperature,
                    "max_output_tokens": settings.max_output_tokens,
                    "store": False,
                },
            )
            text = _response_text(response)
            model = response.get("model")
            usage = response.get("usage", {})
            if not isinstance(model, str) or not model or len(model) > 80:
                raise ValueError("Invalid provider response.")
            if not isinstance(usage, Mapping):
                raise ValueError("Invalid provider response.")
            return ProviderTextResponse(
                request.request_id,
                text,
                model,
                ProviderUsage(
                    _usage_count(usage.get("input_tokens", 0)),
                    _usage_count(usage.get("output_tokens", 0)),
                ),
            )
        except _SafeTransportError as exc:
            return _failure(request, exc.code, exc.retryable)
        except Exception:
            return _failure(request, ProviderFailureCode.PROVIDER_ERROR)


def openai_responses_provider_record() -> ProviderRecord:
    """Return the canonical host-owned remote provider record."""

    return ProviderRecord(
        "builtin/openai-responses",
        ProviderManifest(
            1,
            ProviderMetadata(
                ProviderId(OPENAI_RESPONSES_PROVIDER),
                "OpenAI Responses",
                ProviderVersion(OPENAI_RESPONSES_VERSION),
                ProviderSdkVersion(1),
                "Host-authorized OpenAI Responses API integration.",
                ProviderEntryPoint(
                    "Backend.infrastructure.providers.openai_responses:OpenAIResponsesProvider"
                ),
                ProviderTransport.HTTP,
                ProviderAuthentication.API_KEY,
            ),
            (ProviderCapability.TEXT_GENERATION,),
        ),
        root_id="builtin",
    )


def _post_json(endpoint: str, credential: str, payload: JsonObject) -> Mapping[str, object]:
    request = Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {credential}",
            "Content-Type": "application/json",
            "User-Agent": "UniversalPromptStudio/0.2.0-alpha",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30.0) as response:
            raw = response.read(1_000_001)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise _SafeTransportError(ProviderFailureCode.AUTHENTICATION) from None
        if exc.code == 429:
            raise _SafeTransportError(ProviderFailureCode.RATE_LIMITED, True) from None
        if 500 <= exc.code <= 599:
            raise _SafeTransportError(ProviderFailureCode.SERVICE_UNAVAILABLE, True) from None
        raise _SafeTransportError(ProviderFailureCode.PROVIDER_ERROR) from None
    except TimeoutError:
        raise _SafeTransportError(ProviderFailureCode.TIMEOUT, True) from None
    except (OSError, URLError):
        raise _SafeTransportError(ProviderFailureCode.SERVICE_UNAVAILABLE, True) from None
    if len(raw) > 1_000_000:
        raise _SafeTransportError(ProviderFailureCode.PROVIDER_ERROR)
    try:
        value: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise _SafeTransportError(ProviderFailureCode.PROVIDER_ERROR) from None
    if not isinstance(value, dict):
        raise _SafeTransportError(ProviderFailureCode.PROVIDER_ERROR)
    return value


def _response_text(response: Mapping[str, object]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip() and len(direct) <= 12_500:
        return direct
    output = response.get("output")
    if not isinstance(output, list):
        raise ValueError("Invalid provider response.")
    pieces: list[str] = []
    for item in output:
        if not isinstance(item, Mapping):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    pieces.append(text)
    combined = "".join(pieces)
    if not combined.strip() or len(combined) > 12_500:
        raise ValueError("Invalid provider response.")
    return combined


def _usage_count(value: object) -> int:
    if type(value) is not int or value < 0 or value > 100_000_000:
        raise ValueError("Invalid provider response.")
    return value


def _failure(
    request: ProviderTextRequest,
    code: ProviderFailureCode,
    retryable: bool = False,
) -> ProviderFailure:
    return ProviderFailure(
        request.request_id, code, "Configured provider execution failed safely.", retryable
    )


__all__ = ["OpenAIResponsesProvider", "openai_responses_provider_record"]
