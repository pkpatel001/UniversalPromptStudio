"""Controlled E-016.3 workflow scaffold generation through E-009 and E-008."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

from Engineering.CodeGeneration import (
    ArtifactInfo,
    GenerationContext,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import WorkflowError
from Engineering.Templates import TemplateExecutionResult, TemplateExecutor

from .manifest import (
    WORKFLOW_MANIFEST_NAME,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowManifestReader,
)
from .models import (
    WorkflowEdge,
    WorkflowEndpoint,
    WorkflowEndpointKind,
    WorkflowId,
    WorkflowManifest,
    WorkflowMetadata,
    WorkflowNode,
    WorkflowPort,
    WorkflowSdkVersion,
    WorkflowValueType,
    WorkflowVersion,
)

WORKFLOW_SCAFFOLD_TEMPLATE_ID = "workflow.declarative-basic"
WORKFLOW_SCAFFOLD_TEMPLATE_VERSION = "1.0.0"

_WORKFLOW_INPUT_DESCRIPTION = "Text supplied by the workflow caller."
_WORKFLOW_OUTPUT_DESCRIPTION = "Text returned by the workflow."
_NODE_INPUT_DESCRIPTION = "Text supplied to the operation."
_NODE_OUTPUT_DESCRIPTION = "Text returned by the operation."


@dataclass(frozen=True, slots=True)
class WorkflowScaffoldRequest:
    """Validated input for one project-local passive workflow scaffold."""

    workflow_id: str
    name: str
    description: str
    operation_id: str = "ups.echo-text"
    version: str = "1.0.0"
    sdk_version: int = 1
    destination: str | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowScaffoldResult:
    """Expected workflow definition and delegated E-009 execution result."""

    destination: str
    workflow_manifest: WorkflowManifest
    execution: TemplateExecutionResult


class WorkflowScaffoldService:
    """Compose workflow metadata with E-009 templates and E-008 safe writes."""

    def __init__(
        self,
        executor: TemplateExecutor,
        project: ProjectGenerationInfo,
        project_root: Path,
    ) -> None:
        self._executor = executor
        self._project = project
        self._project_root = project_root.resolve()

    @classmethod
    def built_in(
        cls,
        project_root: Path,
        project: ProjectGenerationInfo,
    ) -> WorkflowScaffoldService:
        return cls(TemplateExecutor.built_in(project_root), project, project_root)

    def generate(self, request: WorkflowScaffoldRequest) -> WorkflowScaffoldResult:
        """Generate a bounded passive scaffold without creating operation code."""

        destination = self._destination(request.workflow_id, request.destination)
        expected = self._manifest(request)
        manifest = WorkflowManifestReader().read_text(
            yaml.safe_dump(self._manifest_data(expected), sort_keys=False)
        )
        if manifest != expected:
            raise WorkflowError("Validated workflow request changed during serialization.")
        values: dict[str, object] = {
            "workflow_id": manifest.metadata.workflow_id.value,
            "workflow_name": manifest.metadata.name,
            "workflow_version": manifest.metadata.version.value,
            "sdk_version": manifest.metadata.sdk_version.api_level,
            "description": manifest.metadata.description,
            "operation_id": manifest.nodes[0].operation,
        }
        context = GenerationContext(
            project=self._project,
            generator=GeneratorInfo(
                generator_id=WORKFLOW_SCAFFOLD_TEMPLATE_ID,
                name="Declarative workflow scaffold",
                version=WORKFLOW_SCAFFOLD_TEMPLATE_VERSION,
            ),
            artifact=ArtifactInfo(
                name=manifest.metadata.name,
                description=manifest.metadata.description,
            ),
        )
        execution = self._executor.execute(
            WORKFLOW_SCAFFOLD_TEMPLATE_ID,
            version=WORKFLOW_SCAFFOLD_TEMPLATE_VERSION,
            destination=destination,
            context=context,
            values=values,
            overwrite=request.overwrite,
            dry_run=request.dry_run,
        )
        if execution.report.success and not request.dry_run:
            generated_path = self._project_root / destination / WORKFLOW_MANIFEST_NAME
            generated_manifest = WorkflowManifestReader().read(generated_path)
            if generated_manifest != manifest:
                raise WorkflowError(
                    "Generated workflow manifest does not match the validated request."
                )
        return WorkflowScaffoldResult(destination, manifest, execution)

    @staticmethod
    def _manifest(request: WorkflowScaffoldRequest) -> WorkflowManifest:
        string_type = WorkflowValueType.STRING
        workflow_input = WorkflowPort("input", string_type, _WORKFLOW_INPUT_DESCRIPTION)
        workflow_output = WorkflowPort("output", string_type, _WORKFLOW_OUTPUT_DESCRIPTION)
        node_input = WorkflowPort("value", string_type, _NODE_INPUT_DESCRIPTION)
        node_output = WorkflowPort("value", string_type, _NODE_OUTPUT_DESCRIPTION)
        return WorkflowManifest(
            WORKFLOW_SCHEMA_VERSION,
            WorkflowMetadata(
                WorkflowId(request.workflow_id),
                request.name,
                WorkflowVersion(request.version),
                WorkflowSdkVersion(request.sdk_version),
                request.description,
            ),
            (workflow_input,),
            (workflow_output,),
            (
                WorkflowNode(
                    "step",
                    request.operation_id,
                    (node_input,),
                    (node_output,),
                ),
            ),
            (
                WorkflowEdge(
                    WorkflowEndpoint(WorkflowEndpointKind.WORKFLOW_INPUT, "input"),
                    WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "step"),
                ),
                WorkflowEdge(
                    WorkflowEndpoint(WorkflowEndpointKind.NODE, "value", "step"),
                    WorkflowEndpoint(WorkflowEndpointKind.WORKFLOW_OUTPUT, "output"),
                ),
            ),
        )

    @staticmethod
    def _manifest_data(manifest: WorkflowManifest) -> dict[str, object]:
        return {
            "schema_version": manifest.schema_version,
            "workflow": {
                "id": manifest.metadata.workflow_id.value,
                "name": manifest.metadata.name,
                "version": manifest.metadata.version.value,
                "sdk_version": manifest.metadata.sdk_version.api_level,
                "description": manifest.metadata.description,
                "inputs": [WorkflowScaffoldService._port_data(port) for port in manifest.inputs],
                "outputs": [WorkflowScaffoldService._port_data(port) for port in manifest.outputs],
                "nodes": [
                    {
                        "id": node.node_id,
                        "operation": node.operation,
                        "inputs": [
                            WorkflowScaffoldService._port_data(port) for port in node.inputs
                        ],
                        "outputs": [
                            WorkflowScaffoldService._port_data(port) for port in node.outputs
                        ],
                    }
                    for node in manifest.nodes
                ],
                "edges": [
                    {
                        "source": WorkflowScaffoldService._endpoint_data(edge.source),
                        "target": WorkflowScaffoldService._endpoint_data(edge.target),
                    }
                    for edge in manifest.edges
                ],
            },
        }

    @staticmethod
    def _port_data(port: WorkflowPort) -> dict[str, object]:
        return {
            "id": port.port_id,
            "type": port.value_type.value,
            "description": port.description,
        }

    @staticmethod
    def _endpoint_data(endpoint: WorkflowEndpoint) -> dict[str, object]:
        if endpoint.kind == WorkflowEndpointKind.WORKFLOW_INPUT:
            return {"workflow_input": endpoint.port_id}
        if endpoint.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT:
            return {"workflow_output": endpoint.port_id}
        if endpoint.node_id is None:
            raise WorkflowError("Node endpoint is missing its node id.")
        return {"node": endpoint.node_id, "port": endpoint.port_id}

    @staticmethod
    def _destination(workflow_id: str, supplied: str | None) -> str:
        value = supplied or f"Workflows/{workflow_id.replace('.', '-')}"
        value = value.replace("\\", "/")
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or len(path.parts) != 2
            or path.parts[0] != "Workflows"
            or path.parts[1] in {"", ".", ".."}
            or ":" in value
        ):
            raise WorkflowError(
                "Workflow scaffold destination must be one direct child of Workflows/."
            )
        return path.as_posix()


__all__ = [
    "WORKFLOW_SCAFFOLD_TEMPLATE_ID",
    "WORKFLOW_SCAFFOLD_TEMPLATE_VERSION",
    "WorkflowScaffoldRequest",
    "WorkflowScaffoldResult",
    "WorkflowScaffoldService",
]
