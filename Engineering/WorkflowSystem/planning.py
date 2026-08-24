"""Deterministic, non-executing workflow plan construction."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from enum import StrEnum

from Engineering.core.exceptions import WorkflowError

from .compatibility import WorkflowSdkContract
from .graph import WorkflowGraphValidator
from .models import (
    WorkflowEdge,
    WorkflowEndpointKind,
    WorkflowNode,
    WorkflowRecord,
)
from .runtime_api import WorkflowOperationRegistration, WorkflowOperationRegistry
from .validation import require_local_id, require_nonempty_text, require_vendor_id


class WorkflowPlanningFailureCode(StrEnum):
    """Stable categories for deterministic planning failures."""

    WORKFLOW_INCOMPATIBLE = "workflow-incompatible"
    GRAPH_INVALID = "graph-invalid"
    HANDLER_MISSING = "handler-missing"
    HANDLER_SDK_MISMATCH = "handler-sdk-mismatch"
    HANDLER_INPUT_MISMATCH = "handler-input-mismatch"
    HANDLER_OUTPUT_MISMATCH = "handler-output-mismatch"


@dataclass(frozen=True, slots=True)
class WorkflowPlanningFailure:
    """One safe, structured reason a workflow plan was not produced."""

    code: WorkflowPlanningFailureCode
    path: str
    message: str
    node_id: str | None = None
    operation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, WorkflowPlanningFailureCode):
            raise WorkflowError(
                "Workflow planning failure code must be WorkflowPlanningFailureCode."
            )
        require_nonempty_text(self.path, "Workflow planning failure path", maximum=500)
        require_nonempty_text(self.message, "Workflow planning failure message", maximum=1000)
        if self.node_id is not None:
            require_local_id(self.node_id, "Workflow planning failure node id")
        if self.operation_id is not None:
            require_vendor_id(self.operation_id, "Workflow planning failure operation id")


@dataclass(frozen=True, slots=True)
class WorkflowPlanStep:
    """One topologically ordered node bound to one exact handler snapshot."""

    position: int
    node: WorkflowNode
    handler: WorkflowOperationRegistration
    dependencies: tuple[str, ...]
    input_bindings: tuple[WorkflowEdge, ...]

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise WorkflowError("Workflow plan step position must be a non-negative integer.")
        if not isinstance(self.node, WorkflowNode):
            raise WorkflowError("Workflow plan step node must be WorkflowNode.")
        if not isinstance(self.handler, WorkflowOperationRegistration):
            raise WorkflowError("Workflow plan step handler must be WorkflowOperationRegistration.")
        if self.node.operation != self.handler.operation_id:
            raise WorkflowError("Workflow plan step node operation does not match its handler.")
        if self.node.inputs != self.handler.inputs:
            raise WorkflowError("Workflow plan step handler inputs do not match its node.")
        if self.node.outputs != self.handler.outputs:
            raise WorkflowError("Workflow plan step handler outputs do not match its node.")
        if (
            not isinstance(self.dependencies, tuple)
            or tuple(sorted(set(self.dependencies))) != self.dependencies
        ):
            raise WorkflowError("Workflow plan step dependencies must be a sorted unique tuple.")
        for dependency in self.dependencies:
            require_local_id(dependency, "Workflow plan dependency node id")
        if not isinstance(self.input_bindings, tuple) or not all(
            isinstance(edge, WorkflowEdge) for edge in self.input_bindings
        ):
            raise WorkflowError(
                "Workflow plan step input bindings must be a tuple of WorkflowEdge values."
            )
        if any(
            edge.target.kind != WorkflowEndpointKind.NODE
            or edge.target.node_id != self.node.node_id
            for edge in self.input_bindings
        ):
            raise WorkflowError("Workflow plan step input bindings must target the step node.")


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPlan:
    """Immutable deterministic plan that contains no execution state."""

    record: WorkflowRecord
    steps: tuple[WorkflowPlanStep, ...]
    output_bindings: tuple[WorkflowEdge, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.record, WorkflowRecord):
            raise WorkflowError("Workflow execution plan record must be WorkflowRecord.")
        if not isinstance(self.steps, tuple) or not all(
            isinstance(step, WorkflowPlanStep) for step in self.steps
        ):
            raise WorkflowError(
                "Workflow execution plan steps must be a tuple of WorkflowPlanStep values."
            )
        if tuple(step.position for step in self.steps) != tuple(range(len(self.steps))):
            raise WorkflowError(
                "Workflow execution plan step positions must be contiguous from zero."
            )
        planned_ids = tuple(step.node.node_id for step in self.steps)
        manifest_ids = tuple(node.node_id for node in self.record.manifest.nodes)
        if len(set(planned_ids)) != len(planned_ids) or set(planned_ids) != set(manifest_ids):
            raise WorkflowError(
                "Workflow execution plan must contain every manifest node exactly once."
            )
        positions = {step.node.node_id: step.position for step in self.steps}
        for step in self.steps:
            if step.handler.sdk_version != self.record.manifest.metadata.sdk_version:
                raise WorkflowError(
                    "Workflow execution plan handler SDK does not match the workflow."
                )
            expected_dependencies = WorkflowPlanner._dependencies(self.record, step.node.node_id)
            if step.dependencies != expected_dependencies or any(
                positions[dependency] >= step.position for dependency in step.dependencies
            ):
                raise WorkflowError(
                    "Workflow execution plan dependencies do not match topological order."
                )
            expected_bindings = WorkflowPlanner._input_bindings(self.record, step.node.node_id)
            if step.input_bindings != expected_bindings:
                raise WorkflowError(
                    "Workflow execution plan input bindings do not match the manifest."
                )
        expected_outputs = WorkflowPlanner._output_bindings(self.record)
        if self.output_bindings != expected_outputs:
            raise WorkflowError(
                "Workflow execution plan output bindings do not match the manifest."
            )
        if not isinstance(self.output_bindings, tuple) or not all(
            isinstance(edge, WorkflowEdge) for edge in self.output_bindings
        ):
            raise WorkflowError(
                "Workflow execution plan output bindings must be a tuple of WorkflowEdge values."
            )
        if any(
            edge.target.kind != WorkflowEndpointKind.WORKFLOW_OUTPUT
            for edge in self.output_bindings
        ):
            raise WorkflowError(
                "Workflow execution plan output bindings must target workflow outputs."
            )

    @property
    def workflow_id(self) -> str:
        return self.record.workflow_id

    @property
    def version(self) -> str:
        return self.record.version


@dataclass(frozen=True, slots=True)
class WorkflowPlanningReport:
    """Plan-or-fail result with deterministic structured failure ordering."""

    plan: WorkflowExecutionPlan | None = None
    failures: tuple[WorkflowPlanningFailure, ...] = ()

    def __post_init__(self) -> None:
        if self.plan is not None and not isinstance(self.plan, WorkflowExecutionPlan):
            raise WorkflowError("Workflow planning report plan must be WorkflowExecutionPlan.")
        if not isinstance(self.failures, tuple) or not all(
            isinstance(item, WorkflowPlanningFailure) for item in self.failures
        ):
            raise WorkflowError("Workflow planning report failures must be a tuple of failures.")
        if (self.plan is None) == (not self.failures):
            raise WorkflowError(
                "Workflow planning report must contain either one plan or failures."
            )

    @property
    def passed(self) -> bool:
        return self.plan is not None

    @property
    def summary(self) -> str:
        if self.plan is not None:
            return f"Workflow planning succeeded: {len(self.plan.steps)} steps, 0 failures."
        return f"Workflow planning failed: 0 steps, {len(self.failures)} failures."


class WorkflowPlanner:
    """Validate compatible handler bindings and build a stable topological plan."""

    def __init__(
        self,
        registry: WorkflowOperationRegistry,
        sdk_contract: WorkflowSdkContract | None = None,
    ) -> None:
        if not isinstance(registry, WorkflowOperationRegistry):
            raise WorkflowError("Workflow planning requires WorkflowOperationRegistry.")
        self._registry = registry
        self._sdk_contract = sdk_contract or WorkflowSdkContract()

    def plan(self, record: WorkflowRecord) -> WorkflowPlanningReport:
        """Plan one workflow without importing, registering, or invoking handlers."""

        if not isinstance(record, WorkflowRecord):
            raise WorkflowError("Workflow planner record must be WorkflowRecord.")
        compatibility_issue = self._sdk_contract.issue_for(record)
        if compatibility_issue is not None:
            return WorkflowPlanningReport(
                failures=(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.WORKFLOW_INCOMPATIBLE,
                        "workflow.sdk_version",
                        compatibility_issue.message,
                    ),
                )
            )
        graph_issues = WorkflowGraphValidator().validate(record.manifest)
        if graph_issues:
            return WorkflowPlanningReport(
                failures=tuple(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.GRAPH_INVALID,
                        issue.path,
                        f"{issue.code.value}: {issue.message}",
                    )
                    for issue in graph_issues
                )
            )

        failures: list[WorkflowPlanningFailure] = []
        registrations: dict[str, WorkflowOperationRegistration] = {}
        sdk_version = record.manifest.metadata.sdk_version
        for node in sorted(record.manifest.nodes, key=lambda item: item.node_id):
            try:
                registration = self._registry.resolve(node.operation)
            except WorkflowError:
                failures.append(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.HANDLER_MISSING,
                        f"workflow.nodes.{node.node_id}.operation",
                        f"Workflow operation handler is not registered: {node.operation}.",
                        node.node_id,
                        node.operation,
                    )
                )
                continue
            registrations[node.node_id] = registration
            if registration.sdk_version != sdk_version:
                failures.append(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.HANDLER_SDK_MISMATCH,
                        f"workflow.nodes.{node.node_id}.operation",
                        (
                            f"Handler SDK API level "
                            f"{registration.sdk_version.api_level} does not match "
                            f"workflow SDK API level {sdk_version.api_level}."
                        ),
                        node.node_id,
                        node.operation,
                    )
                )
            if registration.inputs != node.inputs:
                failures.append(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.HANDLER_INPUT_MISMATCH,
                        f"workflow.nodes.{node.node_id}.inputs",
                        "Handler input ports do not exactly match the node contract.",
                        node.node_id,
                        node.operation,
                    )
                )
            if registration.outputs != node.outputs:
                failures.append(
                    WorkflowPlanningFailure(
                        WorkflowPlanningFailureCode.HANDLER_OUTPUT_MISMATCH,
                        f"workflow.nodes.{node.node_id}.outputs",
                        "Handler output ports do not exactly match the node contract.",
                        node.node_id,
                        node.operation,
                    )
                )
        if failures:
            return WorkflowPlanningReport(failures=tuple(failures))

        ordered_nodes = self._topological_nodes(record)
        steps = tuple(
            WorkflowPlanStep(
                position,
                node,
                registrations[node.node_id],
                self._dependencies(record, node.node_id),
                self._input_bindings(record, node.node_id),
            )
            for position, node in enumerate(ordered_nodes)
        )
        return WorkflowPlanningReport(
            plan=WorkflowExecutionPlan(
                record,
                steps,
                self._output_bindings(record),
            )
        )

    @staticmethod
    def _topological_nodes(record: WorkflowRecord) -> tuple[WorkflowNode, ...]:
        nodes = {node.node_id: node for node in record.manifest.nodes}
        indegree = {node_id: 0 for node_id in nodes}
        dependents: dict[str, set[str]] = {node_id: set() for node_id in nodes}
        for edge in record.manifest.edges:
            if (
                edge.source.kind == WorkflowEndpointKind.NODE
                and edge.target.kind == WorkflowEndpointKind.NODE
            ):
                source_id = edge.source.node_id
                target_id = edge.target.node_id
                if (
                    source_id is not None
                    and target_id is not None
                    and target_id not in dependents[source_id]
                ):
                    dependents[source_id].add(target_id)
                    indegree[target_id] += 1
        ready = [node_id for node_id, count in indegree.items() if count == 0]
        heapq.heapify(ready)
        ordered: list[WorkflowNode] = []
        while ready:
            node_id = heapq.heappop(ready)
            ordered.append(nodes[node_id])
            for target_id in sorted(dependents[node_id]):
                indegree[target_id] -= 1
                if indegree[target_id] == 0:
                    heapq.heappush(ready, target_id)
        if len(ordered) != len(nodes):
            raise WorkflowError("Workflow planner received a cyclic graph after validation.")
        return tuple(ordered)

    @staticmethod
    def _dependencies(record: WorkflowRecord, node_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    edge.source.node_id
                    for edge in record.manifest.edges
                    if edge.source.kind == WorkflowEndpointKind.NODE
                    and edge.source.node_id is not None
                    and edge.target.kind == WorkflowEndpointKind.NODE
                    and edge.target.node_id == node_id
                }
            )
        )

    @staticmethod
    def _input_bindings(record: WorkflowRecord, node_id: str) -> tuple[WorkflowEdge, ...]:
        edges = tuple(
            edge
            for edge in record.manifest.edges
            if edge.target.kind == WorkflowEndpointKind.NODE and edge.target.node_id == node_id
        )
        return tuple(sorted(edges, key=WorkflowPlanner._edge_key))

    @staticmethod
    def _output_bindings(record: WorkflowRecord) -> tuple[WorkflowEdge, ...]:
        edges = tuple(
            edge
            for edge in record.manifest.edges
            if edge.target.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT
        )
        return tuple(sorted(edges, key=WorkflowPlanner._edge_key))

    @staticmethod
    def _edge_key(edge: WorkflowEdge) -> tuple[str, str, str, str, str, str]:
        return (
            edge.target.kind.value,
            edge.target.node_id or "",
            edge.target.port_id,
            edge.source.kind.value,
            edge.source.node_id or "",
            edge.source.port_id,
        )


__all__ = [
    "WorkflowExecutionPlan",
    "WorkflowPlanStep",
    "WorkflowPlanner",
    "WorkflowPlanningFailure",
    "WorkflowPlanningFailureCode",
    "WorkflowPlanningReport",
]
