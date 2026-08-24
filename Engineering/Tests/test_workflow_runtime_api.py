"""E-016.4 explicit workflow operation registration tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowOperationHandler,
    WorkflowOperationRegistry,
    WorkflowPort,
    WorkflowSdkVersion,
    WorkflowValueType,
)


def _port(port_id: str, description: str | None = None) -> WorkflowPort:
    return WorkflowPort(
        port_id,
        WorkflowValueType.STRING,
        description or f"{port_id} value.",
    )


class _Handler:
    def __init__(
        self,
        operation_id: str,
        *,
        sdk_version: int = 1,
        inputs: tuple[WorkflowPort, ...] = (),
        outputs: tuple[WorkflowPort, ...] = (),
    ) -> None:
        self._operation_id = operation_id
        self._sdk_version = WorkflowSdkVersion(sdk_version)
        self._inputs = inputs
        self._outputs = outputs
        self.calls = 0

    @property
    def operation_id(self) -> str:
        return self._operation_id

    @property
    def sdk_version(self) -> WorkflowSdkVersion:
        return self._sdk_version

    @property
    def inputs(self) -> tuple[WorkflowPort, ...]:
        return self._inputs

    @property
    def outputs(self) -> tuple[WorkflowPort, ...]:
        return self._outputs

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object]:
        self.calls += 1
        return inputs


def test_registry_snapshots_explicit_handler_without_invoking_it() -> None:
    handler = _Handler(
        "example.echo",
        inputs=(_port("value"),),
        outputs=(_port("result"),),
    )
    registry = WorkflowOperationRegistry()

    registry.register(handler)
    registration = registry.resolve("example.echo")

    assert isinstance(handler, WorkflowOperationHandler)
    assert registration.handler is handler
    assert registration.inputs == (_port("value"),)
    assert registration.outputs == (_port("result"),)
    assert handler.calls == 0
    with pytest.raises(FrozenInstanceError):
        registration.operation_id = "example.changed"  # type: ignore[misc]


def test_registry_orders_handlers_and_rejects_duplicate_identity() -> None:
    registry = WorkflowOperationRegistry()
    registry.register(_Handler("example.zeta"))
    registry.register(_Handler("example.alpha"))

    assert tuple(item.operation_id for item in registry.registrations) == (
        "example.alpha",
        "example.zeta",
    )
    with pytest.raises(WorkflowError, match="already registered"):
        registry.register(_Handler("example.alpha"))


def test_registry_unregisters_exact_handler_and_reports_missing_identity() -> None:
    registry = WorkflowOperationRegistry()
    registry.register(_Handler("example.echo"))

    removed = registry.unregister("example.echo")

    assert removed.operation_id == "example.echo"
    assert registry.registrations == ()
    with pytest.raises(WorkflowError, match="not registered"):
        registry.resolve("example.echo")
    with pytest.raises(WorkflowError, match="not registered"):
        registry.unregister("example.echo")


@pytest.mark.parametrize(
    ("handler", "message"),
    (
        (object(), "does not implement"),
        (_Handler("invalid"), "dot-separated segments"),
    ),
)
def test_registry_rejects_invalid_handler_contracts(handler: object, message: str) -> None:
    with pytest.raises(WorkflowError, match=message):
        WorkflowOperationRegistry().register(handler)  # type: ignore[arg-type]


def test_registry_rejects_non_typed_sdk_and_port_snapshots() -> None:
    class InvalidSdkHandler(_Handler):
        @property
        def sdk_version(self) -> WorkflowSdkVersion:
            return 1  # type: ignore[return-value]

    class InvalidPortsHandler(_Handler):
        @property
        def inputs(self) -> tuple[WorkflowPort, ...]:
            return ("value",)  # type: ignore[return-value]

    with pytest.raises(WorkflowError, match="sdk_version"):
        WorkflowOperationRegistry().register(InvalidSdkHandler("example.echo"))
    with pytest.raises(WorkflowError, match="tuple of WorkflowPort"):
        WorkflowOperationRegistry().register(InvalidPortsHandler("example.echo"))
