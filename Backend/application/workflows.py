"""Bounded A-005 workflow authoring, planning, and execution services."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Protocol

from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_SDK_API_LEVEL,
    WorkflowEdge,
    WorkflowEndpoint,
    WorkflowEndpointKind,
    WorkflowExecutionService,
    WorkflowId,
    WorkflowManifest,
    WorkflowMetadata,
    WorkflowNode,
    WorkflowOperationRegistration,
    WorkflowOperationRegistry,
    WorkflowPlanner,
    WorkflowPlanningReport,
    WorkflowPort,
    WorkflowPortValue,
    WorkflowRecord,
    WorkflowRunOutcome,
    WorkflowRunRequest,
    WorkflowSdkVersion,
    WorkflowValueType,
    WorkflowVersion,
)

MAX_WORKFLOWS = 50
MAX_WORKFLOW_PORTS = 8
MAX_WORKFLOW_NODES = 8
MAX_WORKFLOW_EDGES = 64
MAX_WORKFLOW_DEFINITION_BYTES = 12_000
MAX_WORKFLOW_RUNTIME_STRING_LENGTH = 1_000
MAX_WORKFLOW_RUNTIME_VALUE_BYTES = 6_000


class WorkflowDefinitionStoreError(RuntimeError):
    """Base safe workflow-definition storage failure."""


class InvalidWorkflowDefinitionStoreError(WorkflowDefinitionStoreError):
    """The durable workflow-definition document is malformed or incompatible."""


class WorkflowDefinitionRepository(Protocol):
    """Persistence contract for application-authored schema-1 definitions."""

    def list(self) -> tuple[WorkflowManifest, ...]: ...

    def get(self, workflow_id: str) -> WorkflowManifest | None: ...

    def add(self, manifest: WorkflowManifest) -> None: ...

    def replace(self, workflow_id: str, manifest: WorkflowManifest) -> None: ...

    def delete(self, workflow_id: str) -> bool: ...


class InMemoryWorkflowDefinitionRepository:
    """Deterministic in-memory workflow repository for tests and previews."""

    def __init__(self) -> None:
        self._manifests: dict[str, WorkflowManifest] = {}

    def list(self) -> tuple[WorkflowManifest, ...]:
        return tuple(self._manifests[key] for key in sorted(self._manifests))

    def get(self, workflow_id: str) -> WorkflowManifest | None:
        return self._manifests.get(workflow_id)

    def add(self, manifest: WorkflowManifest) -> None:
        workflow_id = manifest.metadata.workflow_id.value
        if workflow_id in self._manifests:
            raise ValueError("Workflow already exists.")
        self._manifests[workflow_id] = manifest

    def replace(self, workflow_id: str, manifest: WorkflowManifest) -> None:
        if workflow_id not in self._manifests:
            raise LookupError("Workflow does not exist.")
        if manifest.metadata.workflow_id.value != workflow_id:
            raise ValueError("Workflow identity cannot change during update.")
        self._manifests[workflow_id] = manifest

    def delete(self, workflow_id: str) -> bool:
        return self._manifests.pop(workflow_id, None) is not None


class WorkflowAuthoringService:
    """Own bounded durable authoring and reuse the Workflow SDK runtime."""

    def __init__(
        self,
        repository: WorkflowDefinitionRepository,
        operation_registry: WorkflowOperationRegistry,
        execution_service: WorkflowExecutionService,
    ) -> None:
        self._repository = repository
        self._operation_registry = operation_registry
        self._execution_service = execution_service

    def operations(self) -> tuple[WorkflowOperationRegistration, ...]:
        return self._operation_registry.registrations

    def list(self) -> tuple[WorkflowManifest, ...]:
        manifests = self._repository.list()
        for manifest in manifests:
            self._validate_stored_definition(manifest)
        return manifests

    def get(self, workflow_id: str) -> WorkflowManifest:
        manifest = self._repository.get(WorkflowId(workflow_id).value)
        if manifest is None:
            raise LookupError("Workflow does not exist.")
        self._validate_stored_definition(manifest)
        return manifest

    def validate_definition(self, manifest: WorkflowManifest) -> None:
        """Validate one passive definition without changing durable state."""

        self._validate_definition(manifest)

    def _validate_stored_definition(self, manifest: WorkflowManifest) -> None:
        try:
            self._validate_definition(manifest)
        except (ValueError, WorkflowError) as exc:
            raise InvalidWorkflowDefinitionStoreError(
                "Workflow definitions are invalid and were left unchanged."
            ) from exc

    def create(self, manifest: WorkflowManifest) -> WorkflowManifest:
        self._validate_definition(manifest)
        if len(self._repository.list()) >= MAX_WORKFLOWS:
            raise ValueError(f"The workflow library supports at most {MAX_WORKFLOWS} definitions.")
        self._repository.add(manifest)
        return manifest

    def update(self, workflow_id: str, manifest: WorkflowManifest) -> WorkflowManifest:
        normalized_id = WorkflowId(workflow_id).value
        self._validate_definition(manifest)
        if manifest.metadata.workflow_id.value != normalized_id:
            raise ValueError("Workflow identity cannot change during update.")
        self._repository.replace(normalized_id, manifest)
        return manifest

    def delete(self, workflow_id: str) -> None:
        normalized_id = WorkflowId(workflow_id).value
        if not self._repository.delete(normalized_id):
            raise LookupError("Workflow does not exist.")

    def plan(self, workflow_id: str) -> WorkflowPlanningReport:
        manifest = self.get(workflow_id)
        return WorkflowPlanner(self._operation_registry).plan(self._record(manifest))

    def execute(
        self,
        workflow_id: str,
        run_id: str,
        inputs: Sequence[WorkflowPortValue],
    ) -> tuple[WorkflowPlanningReport, WorkflowRunOutcome]:
        report = self.plan(workflow_id)
        if report.plan is None:
            raise ValueError("Workflow must have a valid execution plan before execution.")
        normalized_inputs = tuple(inputs)
        for item in normalized_inputs:
            validate_workflow_runtime_value(item.value)
        outcome = self._execution_service.execute(
            report.plan,
            WorkflowRunRequest(run_id, normalized_inputs),
        )
        return report, outcome

    def _validate_definition(self, manifest: WorkflowManifest) -> None:
        if not isinstance(manifest, WorkflowManifest):
            raise ValueError("Workflow definition must use the schema-1 Workflow SDK model.")
        if manifest.schema_version != WORKFLOW_SCHEMA_VERSION:
            raise ValueError("Workflow definition schema is unsupported.")
        if manifest.metadata.sdk_version.api_level != WORKFLOW_SDK_API_LEVEL:
            raise ValueError("Workflow SDK version is unsupported.")
        if len(manifest.inputs) > MAX_WORKFLOW_PORTS or len(manifest.outputs) > MAX_WORKFLOW_PORTS:
            raise ValueError(f"Workflows support at most {MAX_WORKFLOW_PORTS} boundary ports.")
        if not 1 <= len(manifest.nodes) <= MAX_WORKFLOW_NODES:
            raise ValueError(f"Workflows support 1 to {MAX_WORKFLOW_NODES} nodes.")
        if len(manifest.edges) > MAX_WORKFLOW_EDGES:
            raise ValueError(f"Workflows support at most {MAX_WORKFLOW_EDGES} edges.")
        for node in manifest.nodes:
            registration = self._operation_registry.resolve(node.operation)
            if node.inputs != registration.inputs or node.outputs != registration.outputs:
                raise ValueError("Workflow node ports must match the trusted operation contract.")
        encoded = json.dumps(
            workflow_manifest_data(manifest),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(encoded) > MAX_WORKFLOW_DEFINITION_BYTES:
            raise ValueError("Workflow definition exceeds the supported size.")

    @staticmethod
    def _record(manifest: WorkflowManifest) -> WorkflowRecord:
        workflow_id = manifest.metadata.workflow_id.value
        return WorkflowRecord(
            f"application/{workflow_id}/workflow-manifest.yaml",
            manifest,
            root_id="application",
        )


def workflow_manifest_data(manifest: WorkflowManifest) -> dict[str, object]:
    """Return the canonical passive schema-1 manifest mapping."""

    metadata = manifest.metadata
    return {
        "schema_version": manifest.schema_version,
        "workflow": {
            "id": metadata.workflow_id.value,
            "name": metadata.name,
            "version": metadata.version.value,
            "sdk_version": metadata.sdk_version.api_level,
            "description": metadata.description,
            "inputs": [_port_data(port) for port in manifest.inputs],
            "outputs": [_port_data(port) for port in manifest.outputs],
            "nodes": [
                {
                    "id": node.node_id,
                    "operation": node.operation,
                    "inputs": [_port_data(port) for port in node.inputs],
                    "outputs": [_port_data(port) for port in node.outputs],
                }
                for node in manifest.nodes
            ],
            "edges": [
                {
                    "source": _endpoint_data(edge.source),
                    "target": _endpoint_data(edge.target),
                }
                for edge in manifest.edges
            ],
        },
    }


def workflow_manifest_from_data(value: object) -> WorkflowManifest:
    """Parse exact schema-1 manifest data without requiring a valid graph draft."""

    root = _exact_mapping(value, {"schema_version", "workflow"})
    if root["schema_version"] != WORKFLOW_SCHEMA_VERSION:
        raise ValueError("Workflow definition schema is unsupported.")
    workflow = _exact_mapping(
        root["workflow"],
        {
            "id",
            "name",
            "version",
            "sdk_version",
            "description",
            "inputs",
            "outputs",
            "nodes",
            "edges",
        },
    )
    nodes_value = _bounded_list(workflow["nodes"], MAX_WORKFLOW_NODES)
    edges_value = _bounded_list(workflow["edges"], MAX_WORKFLOW_EDGES)
    return WorkflowManifest(
        schema_version=1,
        metadata=WorkflowMetadata(
            WorkflowId(_text(workflow["id"])),
            _text(workflow["name"]),
            WorkflowVersion(_text(workflow["version"])),
            WorkflowSdkVersion(_integer(workflow["sdk_version"])),
            _text(workflow["description"]),
        ),
        inputs=_ports(workflow["inputs"]),
        outputs=_ports(workflow["outputs"]),
        nodes=tuple(_node(item) for item in nodes_value),
        edges=tuple(_edge(item) for item in edges_value),
    )


def validate_workflow_runtime_value(value: object) -> None:
    """Apply the tighter desktop IPC bound to one SDK-bounded runtime value."""

    thawed = _runtime_json_value(value)
    encoded = json.dumps(
        thawed,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > MAX_WORKFLOW_RUNTIME_VALUE_BYTES:
        raise ValueError("Workflow runtime value exceeds the supported size.")


def _port_data(port: WorkflowPort) -> dict[str, object]:
    return {
        "id": port.port_id,
        "type": port.value_type.value,
        "description": port.description,
    }


def _endpoint_data(endpoint: WorkflowEndpoint) -> dict[str, object]:
    if endpoint.kind == WorkflowEndpointKind.WORKFLOW_INPUT:
        return {"workflow_input": endpoint.port_id}
    if endpoint.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT:
        return {"workflow_output": endpoint.port_id}
    return {"node": endpoint.node_id or "", "port": endpoint.port_id}


def _node(value: object) -> WorkflowNode:
    data = _exact_mapping(value, {"id", "operation", "inputs", "outputs"})
    return WorkflowNode(
        _text(data["id"]),
        _text(data["operation"]),
        _ports(data["inputs"]),
        _ports(data["outputs"]),
    )


def _ports(value: object) -> tuple[WorkflowPort, ...]:
    items = _bounded_list(value, MAX_WORKFLOW_PORTS)
    ports: list[WorkflowPort] = []
    for item in items:
        data = _exact_mapping(item, {"id", "type", "description"})
        ports.append(
            WorkflowPort(
                _text(data["id"]),
                WorkflowValueType(_text(data["type"])),
                _text(data["description"]),
            )
        )
    return tuple(ports)


def _edge(value: object) -> WorkflowEdge:
    data = _exact_mapping(value, {"source", "target"})
    return WorkflowEdge(
        _endpoint(data["source"], source=True),
        _endpoint(data["target"], source=False),
    )


def _endpoint(value: object, *, source: bool) -> WorkflowEndpoint:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Workflow endpoint is invalid.")
    if set(value) == {"node", "port"}:
        return WorkflowEndpoint(
            WorkflowEndpointKind.NODE,
            _text(value["port"]),
            _text(value["node"]),
        )
    field = "workflow_input" if source else "workflow_output"
    if set(value) != {field}:
        raise ValueError("Workflow endpoint is invalid.")
    kind = WorkflowEndpointKind.WORKFLOW_INPUT if source else WorkflowEndpointKind.WORKFLOW_OUTPUT
    return WorkflowEndpoint(kind, _text(value[field]))


def _exact_mapping(value: object, keys: set[str]) -> dict[str, object]:
    if (
        not isinstance(value, dict)
        or not all(isinstance(key, str) for key in value)
        or set(value) != keys
    ):
        raise ValueError("Workflow definition fields are invalid.")
    return value


def _bounded_list(value: object, maximum: int) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError("Workflow definition collection is invalid.")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Workflow definition text is invalid.")
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("Workflow definition integer is invalid.")
    return value


def _runtime_json_value(value: object) -> object:
    if isinstance(value, str):
        if len(value) > MAX_WORKFLOW_RUNTIME_STRING_LENGTH:
            raise ValueError("Workflow runtime text exceeds the supported size.")
        return value
    if type(value) in {bool, int, float}:
        return value
    if isinstance(value, Mapping):
        return {str(key): _runtime_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_runtime_json_value(item) for item in value]
    raise ValueError("Workflow runtime value is not JSON-shaped.")


__all__ = [
    "InMemoryWorkflowDefinitionRepository",
    "InvalidWorkflowDefinitionStoreError",
    "MAX_WORKFLOW_DEFINITION_BYTES",
    "MAX_WORKFLOW_EDGES",
    "MAX_WORKFLOW_NODES",
    "MAX_WORKFLOW_PORTS",
    "MAX_WORKFLOW_RUNTIME_STRING_LENGTH",
    "MAX_WORKFLOW_RUNTIME_VALUE_BYTES",
    "MAX_WORKFLOWS",
    "WorkflowAuthoringService",
    "WorkflowDefinitionRepository",
    "WorkflowDefinitionStoreError",
    "validate_workflow_runtime_value",
    "workflow_manifest_data",
    "workflow_manifest_from_data",
]
