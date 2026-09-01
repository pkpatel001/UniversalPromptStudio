"""Bridge the typed provider SDK to the phase-one application interface."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from Backend.domain.exceptions import AIProviderExecutionError
from Backend.domain.models import PromptExecutionRequest, PromptExecutionResult
from Backend.interfaces.providers import AIProvider
from Engineering.ProviderSystem import (
    ProviderExecutionService,
    ProviderFailure,
    ProviderRequestOption,
    ProviderTextRequest,
)


def _new_request_id() -> str:
    return str(uuid4())


class ProviderRuntimeAIAdapter(AIProvider):
    """Adapt one registered provider identity to the application AIProvider ABC."""

    def __init__(
        self,
        execution: ProviderExecutionService,
        provider_id: str,
        version: str | None = None,
        *,
        request_id_factory: Callable[[], str] = _new_request_id,
    ) -> None:
        self._execution = execution
        self._provider_id = provider_id
        self._version = version
        self._request_id_factory = request_id_factory

    @property
    def name(self) -> str:
        return self._provider_id

    def execute(self, request: PromptExecutionRequest) -> PromptExecutionResult:
        """Translate, invoke once, and translate the correlated SDK outcome."""

        if request.provider_name != self.name:
            raise ValueError(
                f"Provider request targets {request.provider_name!r}, not {self.name!r}."
            )
        model, options = self._translate_parameters(request.parameters)
        sdk_request = ProviderTextRequest(
            self._request_id_factory(),
            request.prompt,
            model,
            options,
        )
        report = self._execution.execute(self.name, sdk_request, self._version)
        if isinstance(report.result, ProviderFailure):
            raise AIProviderExecutionError(
                self.name,
                report.result.code.value,
                report.result.message,
                retryable=report.result.retryable,
            )

        metadata: dict[str, str | int | float | bool] = {
            "provider_id": report.provider_id.value,
            "provider_version": report.version.value,
            "request_id": report.result.request_id,
            "input_units": report.result.usage.input_units,
            "output_units": report.result.usage.output_units,
        }
        if report.result.model is not None:
            metadata["model"] = report.result.model
        return PromptExecutionResult(report.result.text, self.name, metadata)

    @staticmethod
    def _translate_parameters(
        parameters: dict[str, str | int | float | bool],
    ) -> tuple[str | None, tuple[ProviderRequestOption, ...]]:
        normalized = tuple(
            sorted(
                ((name.replace("_", "-"), value) for name, value in parameters.items()),
                key=lambda item: item[0],
            )
        )
        model: str | None = None
        for name, value in normalized:
            if name == "model":
                if not isinstance(value, str):
                    raise ValueError("Provider model parameter must be a string.")
                model = value
        options = tuple(
            ProviderRequestOption(name, value) for name, value in normalized if name != "model"
        )
        return model, options


__all__ = ["ProviderRuntimeAIAdapter"]
