"""Deterministic semantic validation for passive workflow graphs."""

from __future__ import annotations

from collections import defaultdict

from .models import (
    WorkflowEndpoint,
    WorkflowEndpointKind,
    WorkflowIssueCode,
    WorkflowManifest,
    WorkflowNode,
    WorkflowPort,
    WorkflowValidationIssue,
)


class WorkflowGraphValidator:
    """Validate exact references, bindings, types, and schema-1 acyclicity."""

    def validate(self, manifest: WorkflowManifest) -> tuple[WorkflowValidationIssue, ...]:
        workflow_inputs = {port.port_id: port for port in manifest.inputs}
        workflow_outputs = {port.port_id: port for port in manifest.outputs}
        nodes = {node.node_id: node for node in manifest.nodes}
        target_counts: dict[tuple[str, str], int] = defaultdict(int)
        graph: dict[str, set[str]] = {node.node_id: set() for node in manifest.nodes}
        used_workflow_inputs: set[str] = set()
        output_sources: set[str] = set()
        issues: list[WorkflowValidationIssue] = []

        for index, edge in enumerate(manifest.edges):
            source = self._resolve_source(edge.source, workflow_inputs, nodes)
            target = self._resolve_target(edge.target, workflow_outputs, nodes)
            if source is None:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.edges[{index}].source",
                        WorkflowIssueCode.SOURCE_UNKNOWN,
                        "Edge source does not reference a declared workflow input or node output.",
                    )
                )
            if target is None:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.edges[{index}].target",
                        WorkflowIssueCode.TARGET_UNKNOWN,
                        "Edge target does not reference a declared node input or workflow output.",
                    )
                )
            target_key = self._target_key(edge.target)
            target_counts[target_key] += 1
            if target_counts[target_key] > 1:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.edges[{index}].target",
                        WorkflowIssueCode.TARGET_DUPLICATE,
                        "A node input or workflow output may have exactly one incoming binding.",
                    )
                )
            if source is not None and target is not None and source.value_type != target.value_type:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.edges[{index}]",
                        WorkflowIssueCode.TYPE_MISMATCH,
                        f"Edge type {source.value_type.value} does not match "
                        f"target type {target.value_type.value}.",
                    )
                )
            if (
                edge.source.kind == WorkflowEndpointKind.NODE
                and edge.target.kind == WorkflowEndpointKind.NODE
                and edge.source.node_id in nodes
                and edge.target.node_id in nodes
            ):
                source_node_id = edge.source.node_id
                target_node_id = edge.target.node_id
                if source_node_id is not None and target_node_id is not None:
                    graph[source_node_id].add(target_node_id)
            if edge.source.kind == WorkflowEndpointKind.WORKFLOW_INPUT and source is not None:
                used_workflow_inputs.add(edge.source.port_id)
            if (
                edge.source.kind == WorkflowEndpointKind.NODE
                and edge.target.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT
                and edge.source.node_id is not None
            ):
                output_sources.add(edge.source.node_id)

        for node in manifest.nodes:
            for port in node.inputs:
                if target_counts[(node.node_id, port.port_id)] == 0:
                    issues.append(
                        WorkflowValidationIssue(
                            f"workflow.nodes.{node.node_id}.inputs.{port.port_id}",
                            WorkflowIssueCode.NODE_INPUT_UNBOUND,
                            "Every node input must have exactly one incoming binding.",
                        )
                    )
        for port in manifest.outputs:
            if target_counts[("$output", port.port_id)] == 0:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.outputs.{port.port_id}",
                        WorkflowIssueCode.WORKFLOW_OUTPUT_UNBOUND,
                        "Every workflow output must have exactly one incoming binding.",
                    )
                )
        for port in manifest.inputs:
            if port.port_id not in used_workflow_inputs:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.inputs.{port.port_id}",
                        WorkflowIssueCode.WORKFLOW_INPUT_UNUSED,
                        "Every workflow input must contribute to at least one edge.",
                    )
                )
        productive = set(output_sources)
        changed = True
        while changed:
            changed = False
            for source_node, targets in graph.items():
                if source_node not in productive and targets.intersection(productive):
                    productive.add(source_node)
                    changed = True
        for node in manifest.nodes:
            if node.node_id not in productive:
                issues.append(
                    WorkflowValidationIssue(
                        f"workflow.nodes.{node.node_id}",
                        WorkflowIssueCode.NODE_DISCONNECTED,
                        "Every workflow node must contribute to a workflow output.",
                    )
                )
        if self._has_cycle(graph):
            issues.append(
                WorkflowValidationIssue(
                    "workflow.edges",
                    WorkflowIssueCode.CYCLE,
                    "Workflow schema 1 forbids every directed cycle, "
                    "including disconnected cycles.",
                )
            )
        return tuple(
            sorted(issues, key=lambda issue: (issue.path, issue.code.value, issue.message))
        )

    @staticmethod
    def _resolve_source(
        endpoint: WorkflowEndpoint,
        workflow_inputs: dict[str, WorkflowPort],
        nodes: dict[str, WorkflowNode],
    ) -> WorkflowPort | None:
        if endpoint.kind == WorkflowEndpointKind.WORKFLOW_INPUT:
            return workflow_inputs.get(endpoint.port_id)
        node = nodes.get(endpoint.node_id or "")
        if node is None:
            return None
        return next((port for port in node.outputs if port.port_id == endpoint.port_id), None)

    @staticmethod
    def _resolve_target(
        endpoint: WorkflowEndpoint,
        workflow_outputs: dict[str, WorkflowPort],
        nodes: dict[str, WorkflowNode],
    ) -> WorkflowPort | None:
        if endpoint.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT:
            return workflow_outputs.get(endpoint.port_id)
        node = nodes.get(endpoint.node_id or "")
        if node is None:
            return None
        return next((port for port in node.inputs if port.port_id == endpoint.port_id), None)

    @staticmethod
    def _target_key(endpoint: WorkflowEndpoint) -> tuple[str, str]:
        if endpoint.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT:
            return ("$output", endpoint.port_id)
        return (endpoint.node_id or "", endpoint.port_id)

    @staticmethod
    def _has_cycle(graph: dict[str, set[str]]) -> bool:
        state: dict[str, int] = {}

        def visit(node_id: str) -> bool:
            if state.get(node_id) == 1:
                return True
            if state.get(node_id) == 2:
                return False
            state[node_id] = 1
            if any(visit(target) for target in sorted(graph[node_id])):
                return True
            state[node_id] = 2
            return False

        return any(visit(node_id) for node_id in sorted(graph) if state.get(node_id) != 2)
