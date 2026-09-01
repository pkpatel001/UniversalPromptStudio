"""Typed A-005 workflow commands kept behind the fixed application router."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast
from uuid import UUID

from Backend.application.workflows import (
    InvalidWorkflowDefinitionStoreError,
    WorkflowDefinitionStoreError,
    validate_workflow_runtime_value,
    workflow_manifest_data,
    workflow_manifest_from_data,
)
from Backend.core.container import ApplicationContainer
from Backend.infrastructure.workflow_definitions import PROMPT_EXECUTION_OPERATION_ID
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowPlanningReport,
    WorkflowPort,
    WorkflowPortValue,
    WorkflowRunFailure,
    WorkflowRunSuccess,
)

from .models import IpcErrorCode, IpcRequest, IpcResponse, JsonValue

WORKFLOW_OPERATIONS_COMMAND = "workflows.operations.list"
WORKFLOW_LIST_COMMAND = "workflows.list"
WORKFLOW_CREATE_COMMAND = "workflows.create"
WORKFLOW_GET_COMMAND = "workflows.get"
WORKFLOW_UPDATE_COMMAND = "workflows.update"
WORKFLOW_DELETE_COMMAND = "workflows.delete"
WORKFLOW_PLAN_COMMAND = "workflows.plan"
WORKFLOW_EXECUTE_COMMAND = "workflows.execute"
WORKFLOW_SUPPORTED_COMMANDS = (
    WORKFLOW_OPERATIONS_COMMAND,
    WORKFLOW_LIST_COMMAND,
    WORKFLOW_CREATE_COMMAND,
    WORKFLOW_GET_COMMAND,
    WORKFLOW_UPDATE_COMMAND,
    WORKFLOW_DELETE_COMMAND,
    WORKFLOW_PLAN_COMMAND,
    WORKFLOW_EXECUTE_COMMAND,
)


def handle_workflow_command(
    container: ApplicationContainer,
    request: IpcRequest,
) -> IpcResponse:
    """Dispatch one known workflow command through the application service."""

    handlers = {
        WORKFLOW_OPERATIONS_COMMAND: _operations,
        WORKFLOW_LIST_COMMAND: _list,
        WORKFLOW_CREATE_COMMAND: _create,
        WORKFLOW_GET_COMMAND: _get,
        WORKFLOW_UPDATE_COMMAND: _update,
        WORKFLOW_DELETE_COMMAND: _delete,
        WORKFLOW_PLAN_COMMAND: _plan,
        WORKFLOW_EXECUTE_COMMAND: _execute,
    }
    try:
        result = handlers[request.command](container, request.payload)
    except InvalidWorkflowDefinitionStoreError:
        return IpcResponse.failure(
            request.request_id,
            IpcErrorCode.WORKFLOW_STORAGE_INVALID,
            "Workflow definitions are invalid and were left unchanged.",
        )
    except WorkflowDefinitionStoreError:
        return IpcResponse.failure(
            request.request_id,
            IpcErrorCode.STORAGE_UNAVAILABLE,
            "Workflow definition storage is unavailable.",
        )
    except WorkflowError as exc:
        raise ValueError("Workflow payload is invalid.") from exc
    return IpcResponse.success(request.request_id, result)


def _operations(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, set())
    operations: list[JsonValue] = []
    for registration in container.workflow_authoring_service.operations():
        operations.append(
            {
                "operation_id": registration.operation_id,
                "sdk_version": registration.sdk_version.api_level,
                "inputs": [_port_value(item) for item in registration.inputs],
                "outputs": [_port_value(item) for item in registration.outputs],
                "requires_provider": (registration.operation_id == PROMPT_EXECUTION_OPERATION_ID),
            }
        )
    return {"operations": operations}


def _list(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, set())
    workflows: list[JsonValue] = [
        {
            "workflow_id": manifest.metadata.workflow_id.value,
            "name": manifest.metadata.name,
            "version": manifest.metadata.version.value,
            "description": manifest.metadata.description,
            "node_count": len(manifest.nodes),
            "edge_count": len(manifest.edges),
        }
        for manifest in container.workflow_authoring_service.list()
    ]
    return {"workflows": workflows, "has_more": False}


def _create(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow"})
    manifest = workflow_manifest_from_data(payload["workflow"])
    created = container.workflow_authoring_service.create(manifest)
    return {"workflow": _json_mapping(workflow_manifest_data(created))}


def _get(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow_id"})
    manifest = container.workflow_authoring_service.get(_workflow_id(payload["workflow_id"]))
    return {"workflow": _json_mapping(workflow_manifest_data(manifest))}


def _update(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow_id", "workflow"})
    workflow_id = _workflow_id(payload["workflow_id"])
    manifest = workflow_manifest_from_data(payload["workflow"])
    updated = container.workflow_authoring_service.update(workflow_id, manifest)
    return {"workflow": _json_mapping(workflow_manifest_data(updated))}


def _delete(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow_id", "confirm"})
    workflow_id = _workflow_id(payload["workflow_id"])
    if payload["confirm"] is not True:
        raise ValueError("Workflow deletion requires explicit confirmation.")
    container.workflow_authoring_service.delete(workflow_id)
    return {"deleted_workflow_id": workflow_id}


def _plan(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow_id"})
    report = container.workflow_authoring_service.plan(_workflow_id(payload["workflow_id"]))
    return {"plan": _plan_value(report)}


def _execute(
    container: ApplicationContainer,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _require_fields(payload, {"workflow_id", "run_id", "inputs", "confirm"})
    workflow_id = _workflow_id(payload["workflow_id"])
    run_id = _canonical_uuid(payload["run_id"])
    if payload["confirm"] is not True:
        raise ValueError("Workflow execution requires explicit confirmation.")
    raw_inputs = payload["inputs"]
    if not isinstance(raw_inputs, list) or len(raw_inputs) > 8:
        raise ValueError("Workflow inputs are invalid.")
    inputs: list[WorkflowPortValue] = []
    for raw_input in raw_inputs:
        data = _exact_mapping(raw_input, {"port_id", "value"})
        port_id = data["port_id"]
        if not isinstance(port_id, str):
            raise ValueError("Workflow input port id is invalid.")
        validate_workflow_runtime_value(data["value"])
        inputs.append(WorkflowPortValue(port_id, data["value"]))
    _report, outcome = container.workflow_authoring_service.execute(
        workflow_id,
        run_id,
        inputs,
    )
    return {"execution": _execution_value(outcome)}


def _plan_value(report: WorkflowPlanningReport) -> dict[str, JsonValue]:
    if report.plan is None:
        failures: list[JsonValue] = [
            {
                "code": failure.code.value,
                "path": failure.path,
                "message": failure.message,
                "node_id": failure.node_id,
                "operation_id": failure.operation_id,
            }
            for failure in report.failures
        ]
        return {
            "valid": False,
            "summary": report.summary,
            "workflow_id": None,
            "version": None,
            "steps": [],
            "failures": failures,
        }
    steps: list[JsonValue] = [
        {
            "position": step.position,
            "node_id": step.node.node_id,
            "operation_id": step.node.operation,
            "dependencies": list(step.dependencies),
        }
        for step in report.plan.steps
    ]
    return {
        "valid": True,
        "summary": report.summary,
        "workflow_id": report.plan.workflow_id,
        "version": report.plan.version,
        "steps": steps,
        "failures": [],
    }


def _execution_value(
    outcome: WorkflowRunSuccess | WorkflowRunFailure,
) -> dict[str, JsonValue]:
    completed = (
        outcome.steps if isinstance(outcome, WorkflowRunSuccess) else outcome.completed_steps
    )
    steps: list[JsonValue] = [
        {
            "position": position,
            "node_id": step.node_id,
            "operation_id": step.operation_id,
            "outputs": [_port_runtime_value(item) for item in step.outputs],
        }
        for position, step in enumerate(completed)
    ]
    outputs: list[JsonValue] = (
        [_port_runtime_value(item) for item in outcome.outputs]
        if isinstance(outcome, WorkflowRunSuccess)
        else []
    )
    failure: JsonValue = None
    if isinstance(outcome, WorkflowRunFailure):
        failure = {
            "code": outcome.code.value,
            "message": outcome.message,
            "node_id": outcome.node_id,
            "operation_id": outcome.operation_id,
        }
    return {
        "run_id": outcome.run_id,
        "workflow_id": outcome.workflow_id.value,
        "version": outcome.version.value,
        "succeeded": outcome.succeeded,
        "completed_step_count": len(completed),
        "outputs": outputs,
        "steps": steps,
        "failure": failure,
    }


def _port_value(port: WorkflowPort) -> dict[str, JsonValue]:
    return {
        "port_id": port.port_id,
        "value_type": port.value_type.value,
        "description": port.description,
    }


def _port_runtime_value(value: WorkflowPortValue) -> dict[str, JsonValue]:
    validate_workflow_runtime_value(value.value)
    return {"port_id": value.port_id, "value": _json_value(value.value)}


def _require_fields(payload: dict[str, JsonValue], expected: set[str]) -> None:
    if set(payload) != expected:
        raise ValueError("Workflow payload fields are invalid.")


def _workflow_id(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise ValueError("Workflow identity is invalid.")
    return value


def _canonical_uuid(value: JsonValue) -> str:
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Workflow run identity is invalid.")
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("Workflow run identity is invalid.")
    return value


def _exact_mapping(value: object, keys: set[str]) -> dict[str, JsonValue]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Workflow payload object is invalid.")
    return cast(dict[str, JsonValue], value)


def _json_mapping(value: dict[str, object]) -> dict[str, JsonValue]:
    return {key: _json_value(item) for key, item in value.items()}


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("Workflow result object is invalid.")
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    raise ValueError("Workflow result value is invalid.")


__all__ = [
    "WORKFLOW_CREATE_COMMAND",
    "WORKFLOW_DELETE_COMMAND",
    "WORKFLOW_EXECUTE_COMMAND",
    "WORKFLOW_GET_COMMAND",
    "WORKFLOW_LIST_COMMAND",
    "WORKFLOW_OPERATIONS_COMMAND",
    "WORKFLOW_PLAN_COMMAND",
    "WORKFLOW_SUPPORTED_COMMANDS",
    "WORKFLOW_UPDATE_COMMAND",
    "handle_workflow_command",
]
