"""Host-authored deterministic workflow handlers and offline reference graph."""

from __future__ import annotations

from collections.abc import Mapping

from Engineering.core.exceptions import WorkflowError

from .models import (
    WorkflowEdge,
    WorkflowEndpoint,
    WorkflowEndpointKind,
    WorkflowId,
    WorkflowManifest,
    WorkflowMetadata,
    WorkflowNode,
    WorkflowPort,
    WorkflowRecord,
    WorkflowSdkVersion,
    WorkflowValueType,
    WorkflowVersion,
)
from .planning import WorkflowExecutionPlan, WorkflowPlanner
from .runtime_api import WorkflowOperationRegistry

OFFLINE_ECHO_OPERATION_ID = "ups.echo-text"
OFFLINE_UPPERCASE_OPERATION_ID = "ups.uppercase-text"
OFFLINE_TEXT_WORKFLOW_ID = WorkflowId("ups.offline-text-flow")
OFFLINE_TEXT_WORKFLOW_VERSION = WorkflowVersion("1.0.0")

_INPUT_DESCRIPTION = "Text supplied to the operation."
_OUTPUT_DESCRIPTION = "Text returned by the operation."


def _input_port() -> WorkflowPort:
    return WorkflowPort("value", WorkflowValueType.STRING, _INPUT_DESCRIPTION)


def _output_port() -> WorkflowPort:
    return WorkflowPort("value", WorkflowValueType.STRING, _OUTPUT_DESCRIPTION)


class OfflineEchoWorkflowHandler:
    """Pass through one string without external access or side effects."""

    @property
    def operation_id(self) -> str:
        return OFFLINE_ECHO_OPERATION_ID

    @property
    def sdk_version(self) -> WorkflowSdkVersion:
        return WorkflowSdkVersion(1)

    @property
    def inputs(self) -> tuple[WorkflowPort, ...]:
        return (_input_port(),)

    @property
    def outputs(self) -> tuple[WorkflowPort, ...]:
        return (_output_port(),)

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object]:
        return {"value": inputs["value"]}


class OfflineUppercaseWorkflowHandler:
    """Uppercase one validated string deterministically and offline."""

    @property
    def operation_id(self) -> str:
        return OFFLINE_UPPERCASE_OPERATION_ID

    @property
    def sdk_version(self) -> WorkflowSdkVersion:
        return WorkflowSdkVersion(1)

    @property
    def inputs(self) -> tuple[WorkflowPort, ...]:
        return (_input_port(),)

    @property
    def outputs(self) -> tuple[WorkflowPort, ...]:
        return (_output_port(),)

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object]:
        value = inputs["value"]
        if not isinstance(value, str):
            raise WorkflowError("Offline uppercase handler requires a string.")
        return {"value": value.upper()}


def register_offline_workflow_handlers(
    registry: WorkflowOperationRegistry,
) -> tuple[OfflineEchoWorkflowHandler, OfflineUppercaseWorkflowHandler]:
    """Create and explicitly register the two trusted offline handlers."""

    if not isinstance(registry, WorkflowOperationRegistry):
        raise WorkflowError("Offline workflow handlers require WorkflowOperationRegistry.")
    echo = OfflineEchoWorkflowHandler()
    uppercase = OfflineUppercaseWorkflowHandler()
    registry.register(echo)
    registry.register(uppercase)
    return echo, uppercase


def offline_text_workflow_record() -> WorkflowRecord:
    """Return the canonical two-step host-authored offline workflow."""

    workflow_input = WorkflowPort(
        "input",
        WorkflowValueType.STRING,
        "Text supplied by the workflow caller.",
    )
    workflow_output = WorkflowPort(
        "output",
        WorkflowValueType.STRING,
        "Uppercase text returned by the workflow.",
    )
    echo = WorkflowNode(
        "echo",
        OFFLINE_ECHO_OPERATION_ID,
        (_input_port(),),
        (_output_port(),),
    )
    uppercase = WorkflowNode(
        "uppercase",
        OFFLINE_UPPERCASE_OPERATION_ID,
        (_input_port(),),
        (_output_port(),),
    )
    return WorkflowRecord(
        "offline-text-flow/workflow-manifest.yaml",
        WorkflowManifest(
            1,
            WorkflowMetadata(
                OFFLINE_TEXT_WORKFLOW_ID,
                "UPS Offline Text Flow",
                OFFLINE_TEXT_WORKFLOW_VERSION,
                WorkflowSdkVersion(1),
                "Host-authored deterministic offline sequential workflow.",
            ),
            (workflow_input,),
            (workflow_output,),
            (uppercase, echo),
            (
                WorkflowEdge(
                    WorkflowEndpoint(
                        WorkflowEndpointKind.WORKFLOW_INPUT,
                        "input",
                    ),
                    WorkflowEndpoint(
                        WorkflowEndpointKind.NODE,
                        "value",
                        "echo",
                    ),
                ),
                WorkflowEdge(
                    WorkflowEndpoint(
                        WorkflowEndpointKind.NODE,
                        "value",
                        "echo",
                    ),
                    WorkflowEndpoint(
                        WorkflowEndpointKind.NODE,
                        "value",
                        "uppercase",
                    ),
                ),
                WorkflowEdge(
                    WorkflowEndpoint(
                        WorkflowEndpointKind.NODE,
                        "value",
                        "uppercase",
                    ),
                    WorkflowEndpoint(
                        WorkflowEndpointKind.WORKFLOW_OUTPUT,
                        "output",
                    ),
                ),
            ),
        ),
        root_id="builtin",
    )


def offline_text_workflow_plan(
    registry: WorkflowOperationRegistry,
) -> WorkflowExecutionPlan:
    """Plan the canonical offline workflow against explicit host bindings."""

    report = WorkflowPlanner(registry).plan(offline_text_workflow_record())
    if report.plan is None:
        raise WorkflowError(report.summary)
    return report.plan


__all__ = [
    "OFFLINE_ECHO_OPERATION_ID",
    "OFFLINE_TEXT_WORKFLOW_ID",
    "OFFLINE_TEXT_WORKFLOW_VERSION",
    "OFFLINE_UPPERCASE_OPERATION_ID",
    "OfflineEchoWorkflowHandler",
    "OfflineUppercaseWorkflowHandler",
    "offline_text_workflow_plan",
    "offline_text_workflow_record",
    "register_offline_workflow_handlers",
]
