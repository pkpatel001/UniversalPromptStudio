"""E-016.4 deterministic workflow planning tests."""

from __future__ import annotations

import importlib
import socket
import subprocess
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, replace

import pytest

from Engineering.WorkflowSystem import (
    WorkflowEdge,
    WorkflowEndpoint,
    WorkflowEndpointKind,
    WorkflowExecutionPlan,
    WorkflowId,
    WorkflowManifest,
    WorkflowMetadata,
    WorkflowNode,
    WorkflowOperationRegistry,
    WorkflowPlanner,
    WorkflowPlanningFailureCode,
    WorkflowPort,
    WorkflowRecord,
    WorkflowSdkVersion,
    WorkflowValueType,
    WorkflowVersion,
)


def _port(port_id: str, description: str | None = None) -> WorkflowPort:
    return WorkflowPort(
        port_id,
        WorkflowValueType.STRING,
        description or f"{port_id} value.",
    )


def _node(
    node_id: str,
    operation: str,
    inputs: tuple[WorkflowPort, ...],
    outputs: tuple[WorkflowPort, ...],
) -> WorkflowNode:
    return WorkflowNode(node_id, operation, inputs, outputs)


def _record(
    *, sdk_version: int = 1, edges: tuple[WorkflowEdge, ...] | None = None
) -> WorkflowRecord:
    alpha = _node(
        "alpha",
        "example.alpha",
        (_port("value"),),
        (_port("value"),),
    )
    zeta = _node(
        "zeta",
        "example.zeta",
        (_port("value"),),
        (_port("value"),),
    )
    merge = _node(
        "merge",
        "example.merge",
        (_port("left"), _port("right")),
        (_port("value"),),
    )
    graph_edges = (
        WorkflowEdge(
            WorkflowEndpoint(WorkflowEndpointKind.WORKFLOW_INPUT, "prompt"),
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "zeta"),
        ),
        WorkflowEdge(
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "zeta"),
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "right", "merge"),
        ),
        WorkflowEdge(
            WorkflowEndpoint(WorkflowEndpointKind.WORKFLOW_INPUT, "prompt"),
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "alpha"),
        ),
        WorkflowEdge(
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "alpha"),
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "left", "merge"),
        ),
        WorkflowEdge(
            WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "merge"),
            WorkflowEndpoint(WorkflowEndpointKind.WORKFLOW_OUTPUT, "result"),
        ),
    )
    manifest = WorkflowManifest(
        1,
        WorkflowMetadata(
            WorkflowId("example.branching"),
            "Branching workflow",
            WorkflowVersion("1.0.0"),
            WorkflowSdkVersion(sdk_version),
            "Deterministic planning fixture.",
        ),
        (_port("prompt"),),
        (_port("result"),),
        (merge, zeta, alpha),
        graph_edges if edges is None else edges,
    )
    return WorkflowRecord("branching/workflow-manifest.yaml", manifest)


class _Handler:
    def __init__(
        self,
        node: WorkflowNode,
        *,
        sdk_version: int = 1,
        inputs: tuple[WorkflowPort, ...] | None = None,
        outputs: tuple[WorkflowPort, ...] | None = None,
    ) -> None:
        self._operation_id = node.operation
        self._sdk_version = WorkflowSdkVersion(sdk_version)
        self._inputs = node.inputs if inputs is None else inputs
        self._outputs = node.outputs if outputs is None else outputs
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


def _registry(
    record: WorkflowRecord,
    *,
    alpha_sdk: int = 1,
    alpha_inputs: tuple[WorkflowPort, ...] | None = None,
    alpha_outputs: tuple[WorkflowPort, ...] | None = None,
    omit: str | None = None,
) -> tuple[WorkflowOperationRegistry, dict[str, _Handler]]:
    registry = WorkflowOperationRegistry()
    handlers: dict[str, _Handler] = {}
    for node in record.manifest.nodes:
        if node.node_id == omit:
            continue
        handler = _Handler(
            node,
            sdk_version=alpha_sdk if node.node_id == "alpha" else 1,
            inputs=alpha_inputs if node.node_id == "alpha" else None,
            outputs=alpha_outputs if node.node_id == "alpha" else None,
        )
        handlers[node.node_id] = handler
        registry.register(handler)
    return registry, handlers


def test_planner_builds_stable_topological_plan_without_execution() -> None:
    record = _record()
    registry, handlers = _registry(record)

    report = WorkflowPlanner(registry).plan(record)

    assert report.passed
    assert report.failures == ()
    assert isinstance(report.plan, WorkflowExecutionPlan)
    assert report.plan.workflow_id == "example.branching"
    assert report.plan.version == "1.0.0"
    assert tuple(step.node.node_id for step in report.plan.steps) == (
        "alpha",
        "zeta",
        "merge",
    )
    assert tuple(step.position for step in report.plan.steps) == (0, 1, 2)
    assert report.plan.steps[2].dependencies == ("alpha", "zeta")
    assert tuple(edge.target.port_id for edge in report.plan.steps[2].input_bindings) == (
        "left",
        "right",
    )
    assert report.plan.output_bindings[0].target.port_id == "result"
    assert report.summary == "Workflow planning succeeded: 3 steps, 0 failures."
    assert all(handler.calls == 0 for handler in handlers.values())
    with pytest.raises(FrozenInstanceError):
        report.plan.steps = ()  # type: ignore[misc]


def test_topological_ties_are_independent_of_manifest_and_edge_order() -> None:
    first = _record()
    second_manifest = replace(
        first.manifest,
        nodes=tuple(reversed(first.manifest.nodes)),
        edges=tuple(reversed(first.manifest.edges)),
    )
    second = WorkflowRecord(first.relative_path, second_manifest)
    first_registry, _ = _registry(first)
    second_registry, _ = _registry(second)

    first_plan = WorkflowPlanner(first_registry).plan(first).plan
    second_plan = WorkflowPlanner(second_registry).plan(second).plan

    assert first_plan is not None
    assert second_plan is not None
    assert tuple(step.node.node_id for step in first_plan.steps) == tuple(
        step.node.node_id for step in second_plan.steps
    )


def test_missing_handler_is_a_structured_non_executing_failure() -> None:
    record = _record()
    registry, handlers = _registry(record, omit="zeta")

    report = WorkflowPlanner(registry).plan(record)

    assert not report.passed
    assert report.plan is None
    assert tuple(item.code for item in report.failures) == (
        WorkflowPlanningFailureCode.HANDLER_MISSING,
    )
    assert report.failures[0].node_id == "zeta"
    assert report.failures[0].operation_id == "example.zeta"
    assert report.summary == "Workflow planning failed: 0 steps, 1 failures."
    assert all(handler.calls == 0 for handler in handlers.values())


def test_contract_mismatches_are_complete_and_deterministically_ordered() -> None:
    record = _record()
    registry, handlers = _registry(
        record,
        alpha_sdk=2,
        alpha_inputs=(_port("value", "Different input description."),),
        alpha_outputs=(_port("different"),),
    )

    report = WorkflowPlanner(registry).plan(record)

    assert tuple(item.code for item in report.failures) == (
        WorkflowPlanningFailureCode.HANDLER_SDK_MISMATCH,
        WorkflowPlanningFailureCode.HANDLER_INPUT_MISMATCH,
        WorkflowPlanningFailureCode.HANDLER_OUTPUT_MISMATCH,
    )
    assert all(item.node_id == "alpha" for item in report.failures)
    assert all(handler.calls == 0 for handler in handlers.values())


def test_incompatible_sdk_and_invalid_graph_fail_before_handler_resolution() -> None:
    future = _record(sdk_version=2)
    invalid = _record(edges=())
    empty_registry = WorkflowOperationRegistry()

    future_report = WorkflowPlanner(empty_registry).plan(future)
    invalid_report = WorkflowPlanner(empty_registry).plan(invalid)

    assert tuple(item.code for item in future_report.failures) == (
        WorkflowPlanningFailureCode.WORKFLOW_INCOMPATIBLE,
    )
    assert invalid_report.failures
    assert all(
        item.code == WorkflowPlanningFailureCode.GRAPH_INVALID for item in invalid_report.failures
    )


def test_planning_imports_nothing_and_uses_no_network_or_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()
    registry, handlers = _registry(record)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda *_args, **_kwargs: pytest.fail("operation import attempted"),
    )
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *_args, **_kwargs: pytest.fail("network attempted"),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("subprocess attempted"),
    )

    report = WorkflowPlanner(registry).plan(record)

    assert report.passed
    assert all(handler.calls == 0 for handler in handlers.values())
