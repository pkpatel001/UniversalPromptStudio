"""Immutable E-016.1 workflow SDK and graph models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packaging.version import InvalidVersion, Version

from Engineering.core.exceptions import WorkflowError

from .validation import require_local_id, require_nonempty_text, require_vendor_id


@dataclass(frozen=True, slots=True)
class WorkflowId:
    """Stable vendor-qualified workflow identity."""

    value: str

    def __post_init__(self) -> None:
        require_vendor_id(self.value, "Workflow id")


@dataclass(frozen=True, slots=True)
class WorkflowVersion:
    """Canonical PEP 440 workflow definition version."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise WorkflowError(
                "Workflow version must be a non-empty value of at most 64 characters."
            )
        try:
            parsed = Version(self.value)
        except InvalidVersion as exc:
            raise WorkflowError(f"Invalid workflow version: {self.value!r}") from exc
        if (
            str(parsed) != self.value
            or len(parsed.release) != 3
            or parsed.epoch != 0
            or parsed.local is not None
        ):
            raise WorkflowError(
                "Workflow version must use canonical PEP 440 form with exactly "
                "major.minor.patch release components and no epoch or local version."
            )


@dataclass(frozen=True, slots=True)
class WorkflowSdkVersion:
    """Positive Workflow SDK authoring and handler-contract API level."""

    api_level: int

    def __post_init__(self) -> None:
        if type(self.api_level) is not int or self.api_level < 1:
            raise WorkflowError("Workflow sdk_version must be a positive integer API level.")


class WorkflowValueType(StrEnum):
    """Closed schema-1 JSON-shaped workflow port vocabulary."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass(frozen=True, slots=True)
class WorkflowPort:
    """One typed, named workflow or node port."""

    port_id: str
    value_type: WorkflowValueType
    description: str

    def __post_init__(self) -> None:
        require_local_id(self.port_id, "Workflow port id")
        if not isinstance(self.value_type, WorkflowValueType):
            raise WorkflowError("Workflow port type must be WorkflowValueType.")
        require_nonempty_text(self.description, "Workflow port description", maximum=500)


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    """Declarative operation instance with an exact typed port contract."""

    node_id: str
    operation: str
    inputs: tuple[WorkflowPort, ...]
    outputs: tuple[WorkflowPort, ...]

    def __post_init__(self) -> None:
        require_local_id(self.node_id, "Workflow node id")
        require_vendor_id(self.operation, "Workflow operation id")
        if len(self.inputs) > 64 or len(self.outputs) > 64:
            raise WorkflowError("Workflow nodes may declare at most 64 input and 64 output ports.")
        _require_unique_port_ids(self.inputs, f"Workflow node {self.node_id} inputs")
        _require_unique_port_ids(self.outputs, f"Workflow node {self.node_id} outputs")


class WorkflowEndpointKind(StrEnum):
    """The closed set of graph endpoint roles."""

    WORKFLOW_INPUT = "workflow-input"
    NODE = "node"
    WORKFLOW_OUTPUT = "workflow-output"


@dataclass(frozen=True, slots=True)
class WorkflowEndpoint:
    """A workflow boundary port or a port owned by one node."""

    kind: WorkflowEndpointKind
    port_id: str
    node_id: str | None = None

    def __post_init__(self) -> None:
        require_local_id(self.port_id, "Workflow endpoint port id")
        if self.kind == WorkflowEndpointKind.NODE:
            if self.node_id is None:
                raise WorkflowError("Node endpoints must declare a node id.")
            require_local_id(self.node_id, "Workflow endpoint node id")
        elif self.node_id is not None:
            raise WorkflowError("Workflow boundary endpoints cannot declare a node id.")


@dataclass(frozen=True, slots=True)
class WorkflowEdge:
    """One explicit directed data-flow binding."""

    source: WorkflowEndpoint
    target: WorkflowEndpoint

    def __post_init__(self) -> None:
        if self.source.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT:
            raise WorkflowError("Workflow outputs cannot be edge sources.")
        if self.target.kind == WorkflowEndpointKind.WORKFLOW_INPUT:
            raise WorkflowError("Workflow inputs cannot be edge targets.")


@dataclass(frozen=True, slots=True)
class WorkflowMetadata:
    """Portable workflow identity and descriptive metadata."""

    workflow_id: WorkflowId
    name: str
    version: WorkflowVersion
    sdk_version: WorkflowSdkVersion
    description: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.name, "Workflow name", maximum=120)
        require_nonempty_text(self.description, "Workflow description", maximum=1000)


@dataclass(frozen=True, slots=True)
class WorkflowManifest:
    """Canonical schema-1 passive workflow definition."""

    schema_version: int
    metadata: WorkflowMetadata
    inputs: tuple[WorkflowPort, ...]
    outputs: tuple[WorkflowPort, ...]
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkflowError("Workflow manifest schema_version must be integer 1.")
        if len(self.inputs) > 128 or len(self.outputs) > 128:
            raise WorkflowError("Workflow manifests may declare at most 128 inputs and outputs.")
        if not self.nodes or len(self.nodes) > 256:
            raise WorkflowError("Workflow manifests must declare 1-256 nodes.")
        if len(self.edges) > 2048:
            raise WorkflowError("Workflow manifests may declare at most 2048 edges.")
        _require_unique_port_ids(self.inputs, "Workflow inputs")
        _require_unique_port_ids(self.outputs, "Workflow outputs")
        node_ids = tuple(node.node_id for node in self.nodes)
        if len(set(node_ids)) != len(node_ids):
            raise WorkflowError("Workflow node ids must be unique.")


class WorkflowIssueCode(StrEnum):
    """Stable semantic issue identifiers for schema-1 graph validation."""

    SOURCE_UNKNOWN = "workflow.edge.source.unknown"
    TARGET_UNKNOWN = "workflow.edge.target.unknown"
    TYPE_MISMATCH = "workflow.edge.type-mismatch"
    TARGET_DUPLICATE = "workflow.edge.target.duplicate"
    NODE_INPUT_UNBOUND = "workflow.node.input.unbound"
    WORKFLOW_OUTPUT_UNBOUND = "workflow.output.unbound"
    CYCLE = "workflow.graph.cycle"


@dataclass(frozen=True, slots=True)
class WorkflowValidationIssue:
    """One deterministic semantic workflow problem."""

    path: str
    code: WorkflowIssueCode
    message: str


def _require_unique_port_ids(ports: tuple[WorkflowPort, ...], label: str) -> None:
    identifiers = tuple(port.port_id for port in ports)
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowError(f"{label} must use unique port ids.")
