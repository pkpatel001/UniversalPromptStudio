"""E-014.6 provider SDK application-integration tests."""

from __future__ import annotations

import pytest

from Backend.core.container import create_in_memory_container
from Backend.domain.exceptions import AIProviderExecutionError
from Backend.domain.models import PromptExecutionRequest
from Backend.infrastructure.providers import ProviderRuntimeAIAdapter
from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import (
    OfflineEchoProvider,
    ProviderExecutionService,
    ProviderFailure,
    ProviderFailureCode,
    ProviderRuntimeRegistry,
    ProviderTextRequest,
    ProviderVersion,
    offline_echo_provider_record,
)


class _FailingOfflineProvider(OfflineEchoProvider):
    def generate_text(self, request: ProviderTextRequest) -> ProviderFailure:
        return ProviderFailure(
            request.request_id,
            ProviderFailureCode.SERVICE_UNAVAILABLE,
            "Offline fixture unavailable.",
            retryable=True,
        )


def _adapter(provider: OfflineEchoProvider) -> ProviderRuntimeAIAdapter:
    registry = ProviderRuntimeRegistry()
    registry.register(offline_echo_provider_record(), provider)
    return ProviderRuntimeAIAdapter(
        ProviderExecutionService(registry),
        provider.provider_id.value,
        provider.version.value,
        request_id_factory=lambda: "request-1",
    )


def test_adapter_translates_application_request_and_sdk_response() -> None:
    adapter = _adapter(OfflineEchoProvider())

    result = adapter.execute(
        PromptExecutionRequest(
            "Build safely",
            adapter.name,
            {"model": "offline-model", "max_tokens": 20, "temperature": 0.2},
        )
    )

    assert result.output == "[offline provider response]\nBuild safely"
    assert result.provider_name == "ups.offline-echo"
    assert result.metadata == {
        "provider_id": "ups.offline-echo",
        "provider_version": "1.0.0",
        "request_id": "request-1",
        "input_units": 12,
        "output_units": 12,
        "model": "offline-model",
    }


def test_adapter_maps_structured_failure_to_safe_application_error() -> None:
    adapter = _adapter(_FailingOfflineProvider())

    with pytest.raises(AIProviderExecutionError) as captured:
        adapter.execute(PromptExecutionRequest("Hello", adapter.name))

    assert str(captured.value) == "Offline fixture unavailable."
    assert captured.value.provider_name == adapter.name
    assert captured.value.code == "service-unavailable"
    assert captured.value.retryable


def test_adapter_rejects_wrong_target_and_unsafe_or_colliding_parameters() -> None:
    adapter = _adapter(OfflineEchoProvider())

    with pytest.raises(ValueError, match="not 'ups.offline-echo'"):
        adapter.execute(PromptExecutionRequest("Hello", "wrong.provider"))
    with pytest.raises(ProviderError, match="credential material"):
        adapter.execute(PromptExecutionRequest("Hello", adapter.name, {"api_key": "do-not-pass"}))
    with pytest.raises(ProviderError, match="must be unique"):
        adapter.execute(
            PromptExecutionRequest(
                "Hello",
                adapter.name,
                {"top_p": 0.5, "top-p": 0.6},
            )
        )


def test_container_exposes_host_authorized_runtimes_without_replacing_dummy_provider() -> None:
    container = create_in_memory_container()

    assert container.ai_providers.names() == ("dummy", "ups.offline-echo", "ups.openai-responses")
    assert container.provider_runtime_registry.resolve("ups.offline-echo").version == "1.0.0"

    result = container.prompt_execution_service.execute(
        PromptExecutionRequest("Integrated", "ups.offline-echo")
    )
    legacy = container.prompt_execution_service.execute(PromptExecutionRequest("Legacy", "dummy"))

    assert result.output == "[offline provider response]\nIntegrated"
    assert result.metadata["provider_version"] == ProviderVersion("1.0.0").value
    assert legacy.output == "[dummy response]\nLegacy"
