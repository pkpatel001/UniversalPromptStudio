"""Typed, non-executing workflow operation contracts and registration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from Engineering.core.exceptions import WorkflowError

from .models import WorkflowPort, WorkflowSdkVersion
from .validation import require_vendor_id


@runtime_checkable
class WorkflowOperationHandler(Protocol):
    """Structural contract for one already-created host operation handler."""

    @property
    def operation_id(self) -> str:
        """Return the exact stable operation identity implemented by this handler."""

    @property
    def sdk_version(self) -> WorkflowSdkVersion:
        """Return the exact Workflow SDK handler-contract API level."""

    @property
    def inputs(self) -> tuple[WorkflowPort, ...]:
        """Return the exact ordered input-port contract."""

    @property
    def outputs(self) -> tuple[WorkflowPort, ...]:
        """Return the exact ordered output-port contract."""

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object]:
        """Execute only when a later controlled runner explicitly invokes the handler."""


@dataclass(frozen=True, slots=True)
class WorkflowOperationRegistration:
    """One immutable snapshot binding an operation contract to a host handler."""

    operation_id: str
    sdk_version: WorkflowSdkVersion
    inputs: tuple[WorkflowPort, ...]
    outputs: tuple[WorkflowPort, ...]
    handler: WorkflowOperationHandler

    def __post_init__(self) -> None:
        require_vendor_id(self.operation_id, "Workflow operation id")
        if not isinstance(self.sdk_version, WorkflowSdkVersion):
            raise WorkflowError(
                "Workflow operation registration sdk_version must be WorkflowSdkVersion."
            )
        _require_ports(self.inputs, "Workflow operation registration inputs")
        _require_ports(self.outputs, "Workflow operation registration outputs")
        if not isinstance(self.handler, WorkflowOperationHandler):
            raise WorkflowError(
                "Workflow operation handler does not implement WorkflowOperationHandler."
            )
        if (
            self.handler.operation_id != self.operation_id
            or self.handler.sdk_version != self.sdk_version
            or self.handler.inputs != self.inputs
            or self.handler.outputs != self.outputs
        ):
            raise WorkflowError("Workflow operation handler contract changed during registration.")


class WorkflowOperationRegistry:
    """Explicitly bind already-created handlers without loading or invoking code."""

    def __init__(self) -> None:
        self._registrations: dict[str, WorkflowOperationRegistration] = {}

    def register(self, handler: WorkflowOperationHandler) -> None:
        """Snapshot and register one handler without calling its execute method."""

        if not isinstance(handler, WorkflowOperationHandler):
            raise WorkflowError(
                "Workflow operation handler does not implement WorkflowOperationHandler."
            )
        operation_id = handler.operation_id
        sdk_version = handler.sdk_version
        inputs = handler.inputs
        outputs = handler.outputs
        if not isinstance(operation_id, str):
            raise WorkflowError("Workflow operation handler id must be a string.")
        if not isinstance(sdk_version, WorkflowSdkVersion):
            raise WorkflowError(
                "Workflow operation handler sdk_version must be WorkflowSdkVersion."
            )
        _require_ports(inputs, "Workflow operation handler inputs")
        _require_ports(outputs, "Workflow operation handler outputs")
        if operation_id in self._registrations:
            raise WorkflowError(
                f"Workflow operation handler is already registered: {operation_id}."
            )
        self._registrations[operation_id] = WorkflowOperationRegistration(
            operation_id,
            sdk_version,
            inputs,
            outputs,
            handler,
        )

    def unregister(self, operation_id: str) -> WorkflowOperationRegistration:
        """Remove one exact binding; missing identities are explicit errors."""

        require_vendor_id(operation_id, "Workflow operation id")
        try:
            return self._registrations.pop(operation_id)
        except KeyError as exc:
            raise WorkflowError(
                f"Workflow operation handler is not registered: {operation_id}."
            ) from exc

    def resolve(self, operation_id: str) -> WorkflowOperationRegistration:
        """Resolve one exact host-registered operation contract."""

        require_vendor_id(operation_id, "Workflow operation id")
        try:
            return self._registrations[operation_id]
        except KeyError as exc:
            raise WorkflowError(
                f"Workflow operation handler is not registered: {operation_id}."
            ) from exc

    @property
    def registrations(self) -> tuple[WorkflowOperationRegistration, ...]:
        """Return immutable snapshots in deterministic operation-ID order."""

        return tuple(
            self._registrations[operation_id] for operation_id in sorted(self._registrations)
        )


def _require_ports(ports: object, label: str) -> None:
    if not isinstance(ports, tuple) or not all(isinstance(port, WorkflowPort) for port in ports):
        raise WorkflowError(f"{label} must be a tuple of WorkflowPort values.")
    identifiers = tuple(port.port_id for port in ports)
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowError(f"{label} must use unique port ids.")


__all__ = [
    "WorkflowOperationHandler",
    "WorkflowOperationRegistration",
    "WorkflowOperationRegistry",
]
