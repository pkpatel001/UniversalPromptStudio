"""E-016.5 controlled sequential workflow execution tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowExecutionEvent,
    WorkflowExecutionEventKind,
    WorkflowExecutionService,
    WorkflowOperationRegistry,
    WorkflowPlanner,
    WorkflowPort,
    WorkflowPortValue,
    WorkflowRunFailure,
    WorkflowRunFailureCode,
    WorkflowRunRequest,
    WorkflowRunSuccess,
    WorkflowSdkVersion,
    WorkflowValueType,
    offline_text_workflow_record,
)
from Engineering.WorkflowSystem import execution as workflow_execution


class _Handler:
    def __init__(self, node_id: str, behavior: str = "success") -> None:
        node = next(
            item
            for item in offline_text_workflow_record().manifest.nodes
            if item.node_id == node_id
        )
        self._operation_id = node.operation
        self._sdk_version = WorkflowSdkVersion(1)
        self._inputs = node.inputs
        self._outputs = node.outputs
        self.behavior = behavior
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

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object] | object:
        self.calls += 1
        if self.behavior == "exception":
            raise RuntimeError("sensitive handler detail")
        if self.behavior == "wrong-key":
            return {"unexpected": "value"}
        if self.behavior == "wrong-type":
            return {"value": 42}
        value = inputs["value"]
        if self._operation_id == "ups.uppercase-text":
            assert isinstance(value, str)
            return {"value": value.upper()}
        return {"value": value}


class _Sink:
    def __init__(self, fail_on: int | None = None) -> None:
        self.events: list[WorkflowExecutionEvent] = []
        self.fail_on = fail_on
        self.calls = 0

    def publish(self, event: WorkflowExecutionEvent) -> None:
        self.calls += 1
        if self.calls == self.fail_on:
            raise RuntimeError("event sink failed")
        self.events.append(event)


def _runtime(
    *,
    echo: str = "success",
    uppercase: str = "success",
    sink: _Sink | None = None,
) -> tuple[WorkflowExecutionService, object, _Handler, _Handler]:
    echo_handler = _Handler("echo", echo)
    uppercase_handler = _Handler("uppercase", uppercase)
    registry = WorkflowOperationRegistry()
    registry.register(echo_handler)  # type: ignore[arg-type]
    registry.register(uppercase_handler)  # type: ignore[arg-type]
    report = WorkflowPlanner(registry).plan(offline_text_workflow_record())
    assert report.plan is not None
    return WorkflowExecutionService(sink), report.plan, echo_handler, uppercase_handler


def _request(value: object = "Hello") -> WorkflowRunRequest:
    return WorkflowRunRequest(
        "run-1",
        (WorkflowPortValue("input", value),),
    )


def test_executes_validated_plan_sequentially_and_emits_value_free_events() -> None:
    sink = _Sink()
    service, plan, echo, uppercase = _runtime(sink=sink)

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunSuccess)
    assert outcome.succeeded
    assert outcome.outputs == (WorkflowPortValue("output", "HELLO"),)
    assert tuple(step.node_id for step in outcome.steps) == ("echo", "uppercase")
    assert outcome.steps[0].outputs == (WorkflowPortValue("value", "Hello"),)
    assert echo.calls == uppercase.calls == 1
    assert tuple(event.kind for event in sink.events) == (
        WorkflowExecutionEventKind.STARTED,
        WorkflowExecutionEventKind.COMPLETED,
    )
    assert sink.events[1].succeeded is True
    assert sink.events[1].completed_steps == 2
    assert "Hello" not in repr(sink.events)
    with pytest.raises(FrozenInstanceError):
        outcome.outputs = ()  # type: ignore[misc]


@pytest.mark.parametrize("value", (42, True, ("not", "string")))
def test_invalid_input_type_fails_before_events_or_handlers(value: object) -> None:
    sink = _Sink()
    service, plan, echo, uppercase = _runtime(sink=sink)

    outcome = service.execute(plan, _request(value))  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.INPUT_INVALID
    assert outcome.completed_steps == ()
    assert echo.calls == uppercase.calls == 0
    assert sink.events == []


def test_missing_input_fails_before_execution() -> None:
    service, plan, echo, uppercase = _runtime()

    outcome = service.execute(plan, WorkflowRunRequest("run-1", ()))  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.INPUT_INVALID
    assert echo.calls == uppercase.calls == 0


def test_handler_drift_stops_before_changed_handler_and_preserves_partial_results() -> None:
    sink = _Sink()
    service, plan, echo, uppercase = _runtime(sink=sink)
    uppercase._outputs = (
        WorkflowPort(
            "different",
            WorkflowValueType.STRING,
            "Changed contract.",
        ),
    )

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.HANDLER_DRIFT
    assert tuple(step.node_id for step in outcome.completed_steps) == ("echo",)
    assert outcome.node_id == "uppercase"
    assert echo.calls == 1
    assert uppercase.calls == 0
    assert sink.events[-1].failure_code == WorkflowRunFailureCode.HANDLER_DRIFT


def test_handler_exception_is_contained_without_retry_or_detail_leak() -> None:
    service, plan, echo, uppercase = _runtime(uppercase="exception")

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.HANDLER_ERROR
    assert outcome.message == "Workflow operation handler execution failed."
    assert "sensitive" not in outcome.message
    assert tuple(step.node_id for step in outcome.completed_steps) == ("echo",)
    assert echo.calls == uppercase.calls == 1


@pytest.mark.parametrize("behavior", ("wrong-key", "wrong-type"))
def test_invalid_handler_output_stops_later_steps(behavior: str) -> None:
    service, plan, echo, uppercase = _runtime(echo=behavior)

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.OUTPUT_INVALID
    assert outcome.completed_steps == ()
    assert echo.calls == 1
    assert uppercase.calls == 0


def test_start_event_failure_prevents_execution() -> None:
    sink = _Sink(fail_on=1)
    service, plan, echo, uppercase = _runtime(sink=sink)

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.EVENT_DELIVERY_FAILED
    assert echo.calls == uppercase.calls == 0


def test_completion_event_failure_reports_completed_steps_without_retrying() -> None:
    sink = _Sink(fail_on=2)
    service, plan, echo, uppercase = _runtime(sink=sink)

    outcome = service.execute(plan, _request())  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.EVENT_DELIVERY_FAILED
    assert tuple(step.node_id for step in outcome.completed_steps) == (
        "echo",
        "uppercase",
    )
    assert echo.calls == uppercase.calls == 1


def test_rejects_untyped_host_arguments_and_event_sink() -> None:
    with pytest.raises(WorkflowError, match="event sink"):
        WorkflowExecutionService(object())  # type: ignore[arg-type]
    service, plan, _echo, _uppercase = _runtime()
    with pytest.raises(WorkflowError, match="WorkflowExecutionPlan"):
        service.execute(object(), _request())  # type: ignore[arg-type]
    with pytest.raises(WorkflowError, match="WorkflowRunRequest"):
        service.execute(plan, object())  # type: ignore[arg-type]


def test_aggregate_completed_output_budget_stops_later_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    service, plan, echo, uppercase = _runtime()
    monkeypatch.setattr(workflow_execution, "MAX_WORKFLOW_TRANSPORT_NODES", 1)

    outcome = service.execute(plan, request)  # type: ignore[arg-type]

    assert isinstance(outcome, WorkflowRunFailure)
    assert outcome.code == WorkflowRunFailureCode.OUTPUT_INVALID
    assert tuple(step.node_id for step in outcome.completed_steps) == ("echo",)
    assert echo.calls == uppercase.calls == 1
