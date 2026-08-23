"""E-014.5 controlled AI-provider execution tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderEntryPoint,
    ProviderExecutionReport,
    ProviderExecutionService,
    ProviderFailure,
    ProviderFailureCode,
    ProviderId,
    ProviderManifest,
    ProviderMetadata,
    ProviderRecord,
    ProviderRuntimeRegistry,
    ProviderSdkVersion,
    ProviderTextRequest,
    ProviderTextResponse,
    ProviderTransport,
    ProviderVersion,
)


def _record(version: str = "1.0.0") -> ProviderRecord:
    return ProviderRecord(
        f"echo-{version}/ai-provider-manifest.yaml",
        ProviderManifest(
            1,
            ProviderMetadata(
                ProviderId("example.echo-ai"),
                "Echo AI",
                ProviderVersion(version),
                ProviderSdkVersion(1),
                "Controlled execution fixture.",
                ProviderEntryPoint("provider:EchoProvider"),
                ProviderTransport.LOCAL,
                ProviderAuthentication.NONE,
            ),
            (ProviderCapability.TEXT_GENERATION,),
        ),
    )


class _Runtime:
    def __init__(self, version: str = "1.0.0", behavior: str = "success") -> None:
        self._provider_id = ProviderId("example.echo-ai")
        self._version = ProviderVersion(version)
        self.behavior = behavior
        self.calls = 0

    @property
    def provider_id(self) -> ProviderId:
        return self._provider_id

    @property
    def version(self) -> ProviderVersion:
        return self._version

    def generate_text(self, request: ProviderTextRequest) -> object:
        self.calls += 1
        if self.behavior == "failure":
            return ProviderFailure(
                request.request_id,
                ProviderFailureCode.RATE_LIMITED,
                "Try again later.",
                retryable=True,
            )
        if self.behavior == "exception":
            raise RuntimeError("sensitive provider detail")
        if self.behavior == "wrong-request":
            return ProviderTextResponse("another-request", "Wrong")
        if self.behavior == "invalid":
            return "not a provider result"
        return ProviderTextResponse(request.request_id, request.prompt.upper(), request.model)


def _service(*runtimes: _Runtime) -> ProviderExecutionService:
    registry = ProviderRuntimeRegistry()
    for runtime in runtimes:
        registry.register(_record(runtime.version.value), runtime)  # type: ignore[arg-type]
    return ProviderExecutionService(registry)


def test_executes_one_explicit_registration_and_returns_correlated_report() -> None:
    runtime = _Runtime()
    request = ProviderTextRequest("request-1", "hello", "local-model")

    report = _service(runtime).execute("example.echo-ai", request)

    assert report == ProviderExecutionReport(
        ProviderId("example.echo-ai"),
        ProviderVersion("1.0.0"),
        ProviderTextResponse("request-1", "HELLO", "local-model"),
    )
    assert report.succeeded
    assert runtime.calls == 1
    with pytest.raises(FrozenInstanceError):
        report.result = ProviderTextResponse("request-1", "changed")  # type: ignore[misc]


def test_resolves_exact_or_highest_registered_version_before_execution() -> None:
    first = _Runtime("1.0.0")
    second = _Runtime("2.0.0")
    service = _service(second, first)
    request = ProviderTextRequest("request-1", "hello")

    highest = service.execute("example.echo-ai", request)
    exact = service.execute("example.echo-ai", request, "1.0.0")

    assert highest.version == ProviderVersion("2.0.0")
    assert exact.version == ProviderVersion("1.0.0")
    assert first.calls == 1
    assert second.calls == 1


def test_preserves_structured_provider_failure_without_retrying() -> None:
    runtime = _Runtime(behavior="failure")

    report = _service(runtime).execute(
        "example.echo-ai",
        ProviderTextRequest("request-1", "hello"),
    )

    assert not report.succeeded
    assert isinstance(report.result, ProviderFailure)
    assert report.result.code == ProviderFailureCode.RATE_LIMITED
    assert report.result.retryable
    assert runtime.calls == 1


def test_contains_provider_exception_without_disclosing_exception_text() -> None:
    runtime = _Runtime(behavior="exception")

    report = _service(runtime).execute(
        "example.echo-ai",
        ProviderTextRequest("request-1", "hello"),
    )

    assert isinstance(report.result, ProviderFailure)
    assert report.result.code == ProviderFailureCode.PROVIDER_ERROR
    assert report.result.message == "Provider execution failed."
    assert "sensitive" not in report.result.message
    assert runtime.calls == 1


@pytest.mark.parametrize(
    ("behavior", "message"),
    (
        ("wrong-request", "different request"),
        ("invalid", "invalid result"),
    ),
)
def test_normalizes_invalid_provider_results(behavior: str, message: str) -> None:
    report = _service(_Runtime(behavior=behavior)).execute(
        "example.echo-ai",
        ProviderTextRequest("request-1", "hello"),
    )

    assert isinstance(report.result, ProviderFailure)
    assert report.result.request_id == "request-1"
    assert message in report.result.message


def test_blocks_identity_drift_before_invocation() -> None:
    runtime = _Runtime()
    registry = ProviderRuntimeRegistry()
    registry.register(_record(), runtime)  # type: ignore[arg-type]
    runtime._version = ProviderVersion("2.0.0")

    report = ProviderExecutionService(registry).execute(
        "example.echo-ai",
        ProviderTextRequest("request-1", "hello"),
    )

    assert isinstance(report.result, ProviderFailure)
    assert "identity changed" in report.result.message
    assert runtime.calls == 0


def test_selection_and_request_contract_errors_remain_host_errors() -> None:
    service = _service(_Runtime())

    with pytest.raises(ProviderError, match="not registered"):
        service.execute(
            "example.missing-ai",
            ProviderTextRequest("request-1", "hello"),
        )
    with pytest.raises(ProviderError, match="must be ProviderTextRequest"):
        service.execute("example.echo-ai", object())  # type: ignore[arg-type]
