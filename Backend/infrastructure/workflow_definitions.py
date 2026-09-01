"""Atomic workflow persistence and host-owned application operation handlers."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from Backend.application.provider_settings import OPENAI_RESPONSES_PROVIDER
from Backend.application.services import OFFLINE_REFERENCE_PROVIDER, SavedPromptRuntimeService
from Backend.application.workflows import (
    MAX_WORKFLOW_RUNTIME_STRING_LENGTH,
    MAX_WORKFLOWS,
    InvalidWorkflowDefinitionStoreError,
    WorkflowDefinitionStoreError,
    workflow_manifest_data,
    workflow_manifest_from_data,
)
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowManifest,
    WorkflowOperationRegistry,
    WorkflowPort,
    WorkflowSdkVersion,
    WorkflowValueType,
)

WORKFLOW_DEFINITIONS_FILE_NAME = "workflow-definitions.json"
PROMPT_EXECUTION_OPERATION_ID = "ups.execute-saved-prompt"
MAX_WORKFLOW_DEFINITION_STORE_BYTES = 640_000


class JsonWorkflowDefinitionRepository:
    """Atomic exact-shape schema-1 workflow storage below application data."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("Workflow definition path must be absolute.")
        self._path = path

    def list(self) -> tuple[WorkflowManifest, ...]:
        return self._load()

    def get(self, workflow_id: str) -> WorkflowManifest | None:
        return next(
            (
                manifest
                for manifest in self._load()
                if manifest.metadata.workflow_id.value == workflow_id
            ),
            None,
        )

    def add(self, manifest: WorkflowManifest) -> None:
        manifests = list(self._load())
        workflow_id = manifest.metadata.workflow_id.value
        if any(item.metadata.workflow_id.value == workflow_id for item in manifests):
            raise ValueError("Workflow already exists.")
        manifests.append(manifest)
        self._save(manifests)

    def replace(self, workflow_id: str, manifest: WorkflowManifest) -> None:
        manifests = list(self._load())
        index = next(
            (
                position
                for position, item in enumerate(manifests)
                if item.metadata.workflow_id.value == workflow_id
            ),
            None,
        )
        if index is None:
            raise LookupError("Workflow does not exist.")
        if manifest.metadata.workflow_id.value != workflow_id:
            raise ValueError("Workflow identity cannot change during update.")
        manifests[index] = manifest
        self._save(manifests)

    def delete(self, workflow_id: str) -> bool:
        manifests = list(self._load())
        retained = [
            manifest for manifest in manifests if manifest.metadata.workflow_id.value != workflow_id
        ]
        if len(retained) == len(manifests):
            return False
        self._save(retained)
        return True

    def _load(self) -> tuple[WorkflowManifest, ...]:
        if not self._path.exists():
            return ()
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            raise WorkflowDefinitionStoreError("Workflow definitions are unavailable.") from exc
        try:
            if len(raw) > MAX_WORKFLOW_DEFINITION_STORE_BYTES:
                raise ValueError("Workflow definition store is too large.")
            value = json.loads(raw.decode("utf-8"))
            if (
                not isinstance(value, dict)
                or set(value) != {"schema_version", "workflows"}
                or value["schema_version"] != 1
                or not isinstance(value["workflows"], list)
                or len(value["workflows"]) > MAX_WORKFLOWS
            ):
                raise ValueError("Workflow definition store shape is invalid.")
            manifests = tuple(workflow_manifest_from_data(item) for item in value["workflows"])
            identifiers = tuple(item.metadata.workflow_id.value for item in manifests)
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Workflow definition identities must be unique.")
            return tuple(sorted(manifests, key=lambda item: item.metadata.workflow_id.value))
        except (UnicodeError, json.JSONDecodeError, ValueError, WorkflowError) as exc:
            raise InvalidWorkflowDefinitionStoreError(
                "Workflow definitions are invalid and were left unchanged."
            ) from exc

    def _save(self, manifests: Sequence[WorkflowManifest]) -> None:
        ordered = sorted(manifests, key=lambda item: item.metadata.workflow_id.value)
        payload = json.dumps(
            {
                "schema_version": 1,
                "workflows": [workflow_manifest_data(item) for item in ordered],
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(payload) > MAX_WORKFLOW_DEFINITION_STORE_BYTES:
            raise ValueError("Workflow definition store exceeds the supported size.")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                prefix=".workflow-definitions-",
                suffix=".tmp",
                dir=self._path.parent,
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self._path)
            except Exception:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
                raise
        except OSError as exc:
            raise WorkflowDefinitionStoreError("Workflow definitions are unavailable.") from exc


class SavedPromptWorkflowHandler:
    """Execute one durable saved prompt through an existing authorized provider."""

    def __init__(self, runtime_service: SavedPromptRuntimeService) -> None:
        self._runtime_service = runtime_service

    @property
    def operation_id(self) -> str:
        return PROMPT_EXECUTION_OPERATION_ID

    @property
    def sdk_version(self) -> WorkflowSdkVersion:
        return WorkflowSdkVersion(1)

    @property
    def inputs(self) -> tuple[WorkflowPort, ...]:
        value_type = WorkflowValueType.STRING
        return (
            WorkflowPort("project-id", value_type, "Owning durable project identifier."),
            WorkflowPort("prompt-id", value_type, "Durable project-owned prompt identifier."),
            WorkflowPort(
                "provider-id",
                value_type,
                "Existing host-authorized provider identifier selected for this run.",
            ),
        )

    @property
    def outputs(self) -> tuple[WorkflowPort, ...]:
        return (
            WorkflowPort(
                "result",
                WorkflowValueType.STRING,
                "Bounded text returned by the authorized provider.",
            ),
        )

    def execute(self, inputs: Mapping[str, object]) -> Mapping[str, object]:
        project_id = inputs["project-id"]
        prompt_id = inputs["prompt-id"]
        provider_id = inputs["provider-id"]
        if (
            not isinstance(project_id, str)
            or not isinstance(prompt_id, str)
            or not isinstance(provider_id, str)
        ):
            raise WorkflowError("Saved prompt workflow inputs must be strings.")
        if provider_id == OFFLINE_REFERENCE_PROVIDER:
            _composition, result = self._runtime_service.execute_offline(
                project_id,
                prompt_id,
            )
        elif provider_id == OPENAI_RESPONSES_PROVIDER:
            _composition, result = self._runtime_service.execute_configured(
                project_id,
                prompt_id,
                provider_id,
            )
        else:
            raise WorkflowError("Workflow provider identity is not host-authorized.")
        if not result.output or len(result.output) > MAX_WORKFLOW_RUNTIME_STRING_LENGTH:
            raise WorkflowError("Saved prompt workflow output exceeds the supported bound.")
        return {"result": result.output}


def register_application_workflow_handlers(
    registry: WorkflowOperationRegistry,
    runtime_service: SavedPromptRuntimeService,
) -> SavedPromptWorkflowHandler:
    """Explicitly register the application-owned saved-prompt operation."""

    handler = SavedPromptWorkflowHandler(runtime_service)
    registry.register(handler)
    return handler


__all__ = [
    "JsonWorkflowDefinitionRepository",
    "MAX_WORKFLOW_DEFINITION_STORE_BYTES",
    "PROMPT_EXECUTION_OPERATION_ID",
    "SavedPromptWorkflowHandler",
    "WORKFLOW_DEFINITIONS_FILE_NAME",
    "register_application_workflow_handlers",
]
