"""E-014.4 typed provider runtime contract and registration tests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from Engineering.core.exceptions import ProviderError
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
    ProviderRequestOption,
    ProviderRuntimeRegistry,
    ProviderSdkVersion,
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTransport,
    ProviderUsage,
    ProviderVersion,
    RuntimeTextProvider,
)


def _record(
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.TEXT_GENERATION,
    ),
) -> ProviderRecord:
    return ProviderRecord(
        "echo/ai-provider-manifest.yaml",
        ProviderManifest(
            1,
            ProviderMetadata(
                ProviderId("example.echo-ai"),
                "Echo AI",
                ProviderVersion(version),
                ProviderSdkVersion(sdk_version),
                "Offline runtime contract fixture.",
                ProviderEntryPoint("provider:EchoProvider"),
                ProviderTransport.LOCAL,
                ProviderAuthentication.NONE,
            ),
            capabilities,
        ),
    )


class _EchoRuntime:
    def __init__(self, version: str = "1.0.0") -> None:
        self._version = ProviderVersion(version)
        self.calls = 0

    @property
    def provider_id(self) -> ProviderId:
        return ProviderId("example.echo-ai")

    @property
    def version(self) -> ProviderVersion:
        return self._version

    def generate_text(self, request: ProviderTextRequest) -> ProviderTextResponse:
        self.calls += 1
        return ProviderTextResponse(request.request_id, request.prompt, request.model)


def test_request_response_usage_and_failure_are_typed_and_immutable() -> None:
    option = ProviderRequestOption("temperature", 0.2)
    request = ProviderTextRequest("request-1", "Hello", "local-model", (option,))
    response = ProviderTextResponse(
        "request-1",
        "Hi",
        "local-model",
        ProviderUsage(input_units=1, output_units=1),
    )
    failure = ProviderFailure(
        "request-1",
        ProviderFailureCode.SERVICE_UNAVAILABLE,
        "The service is unavailable.",
        retryable=True,
    )

    assert request.options == (option,)
    assert response.usage.output_units == 1
    assert failure.code == ProviderFailureCode.SERVICE_UNAVAILABLE
    with pytest.raises(FrozenInstanceError):
        request.prompt = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("factory", "message"),
    (
        (lambda: ProviderTextRequest("request-1", "   "), "non-whitespace"),
        (
            lambda: ProviderTextRequest(
                "request-1",
                "Hello",
                options=(
                    ProviderRequestOption("temperature", 0.1),
                    ProviderRequestOption("temperature", 0.2),
                ),
            ),
            "must be unique",
        ),
        (lambda: ProviderRequestOption("api-key", "secret"), "credential material"),
        (lambda: ProviderRequestOption("temperature", float("inf")), "must be finite"),
        (lambda: ProviderUsage(input_units=-1), "non-negative integers"),
        (
            lambda: ProviderFailure("request-1", "timeout", "Timed out."),  # type: ignore[arg-type]
            "ProviderFailureCode",
        ),
    ),
)
def test_runtime_values_reject_invalid_or_secret_bearing_inputs(
    factory: Callable[[], object], message: str
) -> None:
    with pytest.raises(ProviderError, match=message):
        factory()


def test_request_options_allow_non_secret_token_count_names() -> None:
    assert ProviderRequestOption("max-tokens", 20).value == 20


def test_registry_binds_explicit_instances_without_executing_them() -> None:
    runtime = _EchoRuntime()
    registry = ProviderRuntimeRegistry()

    registry.register(_record(), runtime)
    registration = registry.resolve("example.echo-ai")

    assert isinstance(runtime, RuntimeTextProvider)
    assert registration.implementation is runtime
    assert runtime.calls == 0


def test_registry_resolves_highest_version_and_orders_deterministically() -> None:
    registry = ProviderRuntimeRegistry()
    registry.register(_record("2.0.0"), _EchoRuntime("2.0.0"))
    registry.register(_record("1.0.0"), _EchoRuntime("1.0.0"))

    assert tuple(item.version for item in registry.registrations) == ("1.0.0", "2.0.0")
    assert registry.resolve("example.echo-ai").version == "2.0.0"
    assert registry.resolve("example.echo-ai", "1.0.0").version == "1.0.0"


def test_registry_rejects_duplicate_and_identity_mismatch() -> None:
    registry = ProviderRuntimeRegistry()
    runtime = _EchoRuntime()
    registry.register(_record(), runtime)

    with pytest.raises(ProviderError, match="already registered"):
        registry.register(_record(), runtime)
    with pytest.raises(ProviderError, match="version does not match"):
        ProviderRuntimeRegistry().register(_record("2.0.0"), runtime)


def test_registry_enforces_sdk_and_text_generation_capability() -> None:
    with pytest.raises(ProviderError, match="SDK API level 2"):
        ProviderRuntimeRegistry().register(_record(sdk_version=2), _EchoRuntime())
    with pytest.raises(ProviderError, match="did not declare"):
        ProviderRuntimeRegistry().register(
            _record(capabilities=(ProviderCapability.EMBEDDINGS,)),
            _EchoRuntime(),
        )


def test_registry_unregisters_exact_identity_and_reports_missing_bindings() -> None:
    registry = ProviderRuntimeRegistry()
    registry.register(_record(), _EchoRuntime())

    removed = registry.unregister("example.echo-ai", "1.0.0")

    assert removed.version == "1.0.0"
    assert registry.registrations == ()
    with pytest.raises(ProviderError, match="not registered"):
        registry.resolve("example.echo-ai")
    with pytest.raises(ProviderError, match="not registered"):
        registry.unregister("example.echo-ai", "1.0.0")
