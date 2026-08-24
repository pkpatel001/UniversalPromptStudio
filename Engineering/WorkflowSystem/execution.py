"""Controlled sequential execution of an already validated workflow plan."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from Engineering.core.exceptions import WorkflowError

from .models import (
    WorkflowEndpointKind,
    WorkflowId,
    WorkflowPort,
    WorkflowVersion,
)
from .planning import WorkflowExecutionPlan, WorkflowPlanStep
from .validation import require_local_id, require_nonempty_text, require_vendor_id
from .values import (
    MAX_WORKFLOW_TRANSPORT_NODES,
    WorkflowPortValue,
    workflow_value_matches,
    workflow_value_weight,
)

MAX_WORKFLOW_RUN_ID_CHARS = 128
MAX_WORKFLOW_RUN_PORTS = 128


class WorkflowRunFailureCode(StrEnum):
    """Stable failure categories for one controlled workflow run."""

    INPUT_INVALID = "input-invalid"
    HANDLER_DRIFT = "handler-drift"
    HANDLER_ERROR = "handler-error"
    OUTPUT_INVALID = "output-invalid"
    EVENT_DELIVERY_FAILED = "event-delivery-failed"


@dataclass(frozen=True, slots=True)
class WorkflowRunRequest:
    """Correlated immutable workflow inputs supplied by a trusted host."""

    run_id: str
    inputs: tuple[WorkflowPortValue, ...]

    def __post_init__(self) -> None:
        _require_run_id(self.run_id)
        _require_port_values(self.inputs, "Workflow run inputs")


@dataclass(frozen=True, slots=True)
class WorkflowStepResult:
    """Validated outputs from one successfully completed plan step."""

    node_id: str
    operation_id: str
    outputs: tuple[WorkflowPortValue, ...]

    def __post_init__(self) -> None:
        require_local_id(self.node_id, "Workflow step result node id")
        require_vendor_id(self.operation_id, "Workflow step result operation id")
        _require_port_values(self.outputs, "Workflow step result outputs")


@dataclass(frozen=True, slots=True)
class WorkflowRunSuccess:
    """Complete validated output from one sequential workflow run."""

    run_id: str
    workflow_id: WorkflowId
    version: WorkflowVersion
    outputs: tuple[WorkflowPortValue, ...]
    steps: tuple[WorkflowStepResult, ...]

    def __post_init__(self) -> None:
        _require_run_id(self.run_id)
        if not isinstance(self.workflow_id, WorkflowId):
            raise WorkflowError("Workflow run success workflow_id must be WorkflowId.")
        if not isinstance(self.version, WorkflowVersion):
            raise WorkflowError("Workflow run success version must be WorkflowVersion.")
        _require_port_values(self.outputs, "Workflow run outputs")
        _require_steps(self.steps)

    @property
    def succeeded(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class WorkflowRunFailure:
    """Safe failure with only validated results from completed steps."""

    run_id: str
    workflow_id: WorkflowId
    version: WorkflowVersion
    code: WorkflowRunFailureCode
    message: str
    completed_steps: tuple[WorkflowStepResult, ...] = ()
    node_id: str | None = None
    operation_id: str | None = None

    def __post_init__(self) -> None:
        _require_run_id(self.run_id)
        if not isinstance(self.workflow_id, WorkflowId):
            raise WorkflowError("Workflow run failure workflow_id must be WorkflowId.")
        if not isinstance(self.version, WorkflowVersion):
            raise WorkflowError("Workflow run failure version must be WorkflowVersion.")
        if not isinstance(self.code, WorkflowRunFailureCode):
            raise WorkflowError("Workflow run failure code must be WorkflowRunFailureCode.")
        require_nonempty_text(self.message, "Workflow run failure message", maximum=1000)
        _require_steps(self.completed_steps)
        if self.node_id is not None:
            require_local_id(self.node_id, "Workflow run failure node id")
        if self.operation_id is not None:
            require_vendor_id(self.operation_id, "Workflow run failure operation id")

    @property
    def succeeded(self) -> bool:
        return False


type WorkflowRunOutcome = WorkflowRunSuccess | WorkflowRunFailure


class WorkflowExecutionEventKind(StrEnum):
    """Bounded lifecycle events emitted without runtime values."""

    STARTED = "started"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class WorkflowExecutionEvent:
    """Safe event metadata for one started or completed workflow run."""

    kind: WorkflowExecutionEventKind
    run_id: str
    workflow_id: WorkflowId
    version: WorkflowVersion
    completed_steps: int = 0
    succeeded: bool | None = None
    failure_code: WorkflowRunFailureCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, WorkflowExecutionEventKind):
            raise WorkflowError("Workflow execution event kind must be WorkflowExecutionEventKind.")
        _require_run_id(self.run_id)
        if not isinstance(self.workflow_id, WorkflowId):
            raise WorkflowError("Workflow execution event workflow_id must be WorkflowId.")
        if not isinstance(self.version, WorkflowVersion):
            raise WorkflowError("Workflow execution event version must be WorkflowVersion.")
        if type(self.completed_steps) is not int or self.completed_steps < 0:
            raise WorkflowError("Workflow execution event completed_steps must be non-negative.")
        if self.kind == WorkflowExecutionEventKind.STARTED:
            if (
                self.completed_steps != 0
                or self.succeeded is not None
                or self.failure_code is not None
            ):
                raise WorkflowError("Workflow started events cannot contain completion state.")
        elif (
            type(self.succeeded) is not bool
            or (self.succeeded and self.failure_code is not None)
            or (not self.succeeded and self.failure_code is None)
        ):
            raise WorkflowError(
                "Workflow completed events require consistent success and failure state."
            )


@runtime_checkable
class WorkflowExecutionEventSink(Protocol):
    """Host-owned destination for safe workflow lifecycle metadata."""

    def publish(self, event: WorkflowExecutionEvent) -> None:
        """Publish one bounded workflow lifecycle event."""


class WorkflowExecutionService:
    """Execute a validated plan once, sequentially, with fail-fast containment."""

    def __init__(
        self,
        event_sink: WorkflowExecutionEventSink | None = None,
    ) -> None:
        if event_sink is not None and not isinstance(event_sink, WorkflowExecutionEventSink):
            raise WorkflowError(
                "Workflow execution event sink must implement WorkflowExecutionEventSink."
            )
        self._event_sink = event_sink

    def execute(
        self,
        plan: WorkflowExecutionPlan,
        request: WorkflowRunRequest,
    ) -> WorkflowRunOutcome:
        """Run each planned handler at most once without loading or retrying."""

        if not isinstance(plan, WorkflowExecutionPlan):
            raise WorkflowError("Workflow execution plan must be WorkflowExecutionPlan.")
        if not isinstance(request, WorkflowRunRequest):
            raise WorkflowError("Workflow execution request must be WorkflowRunRequest.")
        metadata = plan.record.manifest.metadata
        validated_inputs = self._validated_port_values(
            request.inputs,
            plan.record.manifest.inputs,
            "input",
        )
        if isinstance(validated_inputs, str):
            return self._failure(
                plan,
                request.run_id,
                WorkflowRunFailureCode.INPUT_INVALID,
                validated_inputs,
                (),
            )
        if not self._emit(
            WorkflowExecutionEvent(
                WorkflowExecutionEventKind.STARTED,
                request.run_id,
                metadata.workflow_id,
                metadata.version,
            )
        ):
            return self._failure(
                plan,
                request.run_id,
                WorkflowRunFailureCode.EVENT_DELIVERY_FAILED,
                "Workflow start event delivery failed.",
                (),
            )

        completed: list[WorkflowStepResult] = []
        completed_output_nodes = 0
        node_outputs: dict[str, Mapping[str, object]] = {}
        for step in plan.steps:
            drift_failure = self._handler_drift_failure(
                plan, request.run_id, step, tuple(completed)
            )
            if drift_failure is not None:
                self._emit_completed(drift_failure)
                return drift_failure
            step_inputs = self._step_inputs(
                step,
                validated_inputs,
                node_outputs,
            )
            try:
                raw_outputs = step.handler.handler.execute(step_inputs)
            except Exception:
                failure = self._failure(
                    plan,
                    request.run_id,
                    WorkflowRunFailureCode.HANDLER_ERROR,
                    "Workflow operation handler execution failed.",
                    tuple(completed),
                    step,
                )
                self._emit_completed(failure)
                return failure
            validated_outputs = self._handler_outputs(step, raw_outputs)
            if isinstance(validated_outputs, str):
                failure = self._failure(
                    plan,
                    request.run_id,
                    WorkflowRunFailureCode.OUTPUT_INVALID,
                    validated_outputs,
                    tuple(completed),
                    step,
                )
                self._emit_completed(failure)
                return failure
            output_nodes = sum(workflow_value_weight(value) for value in validated_outputs.values())
            if completed_output_nodes + output_nodes > MAX_WORKFLOW_TRANSPORT_NODES:
                failure = self._failure(
                    plan,
                    request.run_id,
                    WorkflowRunFailureCode.OUTPUT_INVALID,
                    (
                        "Workflow completed outputs exceed "
                        f"{MAX_WORKFLOW_TRANSPORT_NODES} total value nodes."
                    ),
                    tuple(completed),
                    step,
                )
                self._emit_completed(failure)
                return failure
            completed_output_nodes += output_nodes
            step_result = WorkflowStepResult(
                step.node.node_id,
                step.node.operation,
                tuple(
                    WorkflowPortValue(port.port_id, validated_outputs[port.port_id])
                    for port in step.node.outputs
                ),
            )
            completed.append(step_result)
            node_outputs[step.node.node_id] = validated_outputs

        outputs_by_id = {
            edge.target.port_id: node_outputs[edge.source.node_id or ""][edge.source.port_id]
            for edge in plan.output_bindings
        }
        success = WorkflowRunSuccess(
            request.run_id,
            metadata.workflow_id,
            metadata.version,
            tuple(
                WorkflowPortValue(port.port_id, outputs_by_id[port.port_id])
                for port in plan.record.manifest.outputs
            ),
            tuple(completed),
        )
        if not self._emit_completed(success):
            return self._failure(
                plan,
                request.run_id,
                WorkflowRunFailureCode.EVENT_DELIVERY_FAILED,
                "Workflow completion event delivery failed.",
                tuple(completed),
            )
        return success

    @staticmethod
    def _validated_port_values(
        values: tuple[WorkflowPortValue, ...],
        ports: tuple[WorkflowPort, ...],
        label: str,
    ) -> Mapping[str, object] | str:
        expected_ids = tuple(port.port_id for port in ports)
        supplied = {item.port_id: item.value for item in values}
        if set(supplied) != set(expected_ids):
            return f"Workflow {label} ports must exactly match: {', '.join(expected_ids)}."
        for port in ports:
            if not workflow_value_matches(supplied[port.port_id], port.value_type):
                return f"Workflow {label} port {port.port_id} must contain {port.value_type.value}."
        return MappingProxyType({port.port_id: supplied[port.port_id] for port in ports})

    @staticmethod
    def _handler_drift_failure(
        plan: WorkflowExecutionPlan,
        run_id: str,
        step: WorkflowPlanStep,
        completed: tuple[WorkflowStepResult, ...],
    ) -> WorkflowRunFailure | None:
        registration = step.handler
        try:
            matches = (
                registration.handler.operation_id == registration.operation_id
                and registration.handler.sdk_version == registration.sdk_version
                and registration.handler.inputs == registration.inputs
                and registration.handler.outputs == registration.outputs
            )
        except Exception:
            matches = False
        if matches:
            return None
        return WorkflowExecutionService._failure(
            plan,
            run_id,
            WorkflowRunFailureCode.HANDLER_DRIFT,
            "Workflow operation handler contract changed after registration.",
            completed,
            step,
        )

    @staticmethod
    def _step_inputs(
        step: WorkflowPlanStep,
        workflow_inputs: Mapping[str, object],
        node_outputs: Mapping[str, Mapping[str, object]],
    ) -> Mapping[str, object]:
        values: dict[str, object] = {}
        for edge in step.input_bindings:
            if edge.source.kind == WorkflowEndpointKind.WORKFLOW_INPUT:
                value = workflow_inputs[edge.source.port_id]
            else:
                value = node_outputs[edge.source.node_id or ""][edge.source.port_id]
            values[edge.target.port_id] = value
        return MappingProxyType({port.port_id: values[port.port_id] for port in step.node.inputs})

    @classmethod
    def _handler_outputs(
        cls,
        step: WorkflowPlanStep,
        raw_outputs: object,
    ) -> Mapping[str, object] | str:
        if not isinstance(raw_outputs, Mapping):
            return "Workflow operation handler returned a non-mapping result."
        try:
            if len(raw_outputs) > MAX_WORKFLOW_RUN_PORTS:
                return (
                    f"Workflow operation handler returned more than "
                    f"{MAX_WORKFLOW_RUN_PORTS} output ports."
                )
            items = list(raw_outputs.items())
            if not all(isinstance(key, str) for key, _value in items):
                return "Workflow operation handler output keys must be strings."
            values = tuple(WorkflowPortValue(key, value) for key, value in items)
            _require_port_values(values, "Workflow handler outputs")
            return cls._validated_port_values(values, step.node.outputs, "output")
        except (WorkflowError, TypeError, ValueError):
            return "Workflow operation handler returned an invalid bounded value."
        except Exception:
            return "Workflow operation handler returned an unreadable result."

    @staticmethod
    def _failure(
        plan: WorkflowExecutionPlan,
        run_id: str,
        code: WorkflowRunFailureCode,
        message: str,
        completed: tuple[WorkflowStepResult, ...],
        step: WorkflowPlanStep | None = None,
    ) -> WorkflowRunFailure:
        metadata = plan.record.manifest.metadata
        return WorkflowRunFailure(
            run_id,
            metadata.workflow_id,
            metadata.version,
            code,
            message,
            completed,
            step.node.node_id if step is not None else None,
            step.node.operation if step is not None else None,
        )

    def _emit_completed(self, outcome: WorkflowRunOutcome) -> bool:
        return self._emit(
            WorkflowExecutionEvent(
                WorkflowExecutionEventKind.COMPLETED,
                outcome.run_id,
                outcome.workflow_id,
                outcome.version,
                len(
                    outcome.steps
                    if isinstance(outcome, WorkflowRunSuccess)
                    else outcome.completed_steps
                ),
                outcome.succeeded,
                (None if isinstance(outcome, WorkflowRunSuccess) else outcome.code),
            )
        )

    def _emit(self, event: WorkflowExecutionEvent) -> bool:
        if self._event_sink is None:
            return True
        try:
            self._event_sink.publish(event)
        except Exception:
            return False
        return True


def _require_run_id(run_id: str) -> None:
    require_nonempty_text(
        run_id,
        "Workflow run id",
        maximum=MAX_WORKFLOW_RUN_ID_CHARS,
    )


def _require_port_values(values: object, label: str) -> None:
    if (
        not isinstance(values, tuple)
        or len(values) > MAX_WORKFLOW_RUN_PORTS
        or not all(isinstance(item, WorkflowPortValue) for item in values)
    ):
        raise WorkflowError(
            f"{label} must contain at most {MAX_WORKFLOW_RUN_PORTS} WorkflowPortValue items."
        )
    identifiers = tuple(item.port_id for item in values)
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowError(f"{label} must use unique port ids.")
    if sum(workflow_value_weight(item.value) for item in values) > (MAX_WORKFLOW_TRANSPORT_NODES):
        raise WorkflowError(f"{label} exceeds {MAX_WORKFLOW_TRANSPORT_NODES} total value nodes.")


def _require_steps(steps: object) -> None:
    if not isinstance(steps, tuple) or not all(
        isinstance(item, WorkflowStepResult) for item in steps
    ):
        raise WorkflowError(
            "Workflow completed steps must be a tuple of WorkflowStepResult values."
        )
    identifiers = tuple(item.node_id for item in steps)
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowError("Workflow completed step node ids must be unique.")


__all__ = [
    "MAX_WORKFLOW_RUN_ID_CHARS",
    "MAX_WORKFLOW_RUN_PORTS",
    "WorkflowExecutionEvent",
    "WorkflowExecutionEventKind",
    "WorkflowExecutionEventSink",
    "WorkflowExecutionService",
    "WorkflowRunFailure",
    "WorkflowRunFailureCode",
    "WorkflowRunOutcome",
    "WorkflowRunRequest",
    "WorkflowRunSuccess",
    "WorkflowStepResult",
]
