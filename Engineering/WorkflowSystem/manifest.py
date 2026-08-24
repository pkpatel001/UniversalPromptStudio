"""Strict, passive schema-1 workflow manifest reader."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from Engineering.core.exceptions import EngineeringError, WorkflowError
from Engineering.core.filesystem import read_yaml

from .graph import WorkflowGraphValidator
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

WORKFLOW_MANIFEST_NAME = "workflow-manifest.yaml"
WORKFLOW_SCHEMA_VERSION = 1
WORKFLOW_SDK_API_LEVEL = 1

_ROOT_KEYS = frozenset({"schema_version", "workflow"})
_WORKFLOW_KEYS = frozenset(
    {"id", "name", "version", "sdk_version", "description", "inputs", "outputs", "nodes", "edges"}
)
_PORT_KEYS = frozenset({"id", "type", "description"})
_NODE_KEYS = frozenset({"id", "operation", "inputs", "outputs"})
_EDGE_KEYS = frozenset({"source", "target"})
_NODE_ENDPOINT_KEYS = frozenset({"node", "port"})
_WORKFLOW_INPUT_ENDPOINT_KEYS = frozenset({"workflow_input"})
_WORKFLOW_OUTPUT_ENDPOINT_KEYS = frozenset({"workflow_output"})
_SECRET_KEY_FRAGMENTS = ("api_key", "credential", "password", "private_key", "secret", "token")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)^[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@"),
)


class WorkflowManifestReader:
    """Parse and validate a workflow without importing or executing operations."""

    def detect_schema_version(self, path: Path) -> int:
        data = self._read(path)
        value = data.get("schema_version")
        if type(value) is not int:
            raise WorkflowError("Workflow manifest schema_version must be an integer.")
        return value

    def read(self, path: Path) -> WorkflowManifest:
        return self._parse(self._read(path))

    def read_text(self, content: str) -> WorkflowManifest:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise WorkflowError("Workflow manifest YAML is malformed.") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise WorkflowError("Workflow manifest could not be read: YAML root must be a mapping.")
        return self._parse(data)

    def _parse(self, data: dict[str, Any]) -> WorkflowManifest:
        self._reject_secret_content(data)
        self._require_exact_keys(data, _ROOT_KEYS, "Workflow manifest")
        schema_version = data["schema_version"]
        if type(schema_version) is not int:
            raise WorkflowError("Workflow manifest schema_version must be an integer.")
        if schema_version != WORKFLOW_SCHEMA_VERSION:
            raise WorkflowError(
                f"Unsupported workflow manifest schema_version: {schema_version!r}."
            )
        workflow = self._require_mapping(data["workflow"], "workflow")
        self._require_exact_keys(workflow, _WORKFLOW_KEYS, "workflow")
        manifest = WorkflowManifest(
            schema_version=schema_version,
            metadata=WorkflowMetadata(
                WorkflowId(self._require_string(workflow, "id", "workflow")),
                self._require_string(workflow, "name", "workflow"),
                WorkflowVersion(self._require_string(workflow, "version", "workflow")),
                WorkflowSdkVersion(self._require_integer(workflow, "sdk_version", "workflow")),
                self._require_string(workflow, "description", "workflow"),
            ),
            inputs=self._read_ports(workflow["inputs"], "workflow.inputs"),
            outputs=self._read_ports(workflow["outputs"], "workflow.outputs"),
            nodes=self._read_nodes(workflow["nodes"]),
            edges=self._read_edges(workflow["edges"]),
        )
        issues = WorkflowGraphValidator().validate(manifest)
        if issues:
            issue = issues[0]
            raise WorkflowError(f"{issue.code.value} at {issue.path}: {issue.message}")
        return manifest

    def _read_ports(self, value: object, label: str) -> tuple[WorkflowPort, ...]:
        items = self._require_list(value, label)
        ports: list[WorkflowPort] = []
        for index, item in enumerate(items):
            item_label = f"{label}[{index}]"
            port = self._require_mapping(item, item_label)
            self._require_exact_keys(port, _PORT_KEYS, item_label)
            ports.append(
                WorkflowPort(
                    self._require_string(port, "id", item_label),
                    self._read_enum(
                        WorkflowValueType,
                        port["type"],
                        f"{item_label}.type",
                    ),
                    self._require_string(port, "description", item_label),
                )
            )
        return tuple(ports)

    def _read_nodes(self, value: object) -> tuple[WorkflowNode, ...]:
        items = self._require_list(value, "workflow.nodes")
        nodes: list[WorkflowNode] = []
        for index, item in enumerate(items):
            label = f"workflow.nodes[{index}]"
            node = self._require_mapping(item, label)
            self._require_exact_keys(node, _NODE_KEYS, label)
            nodes.append(
                WorkflowNode(
                    self._require_string(node, "id", label),
                    self._require_string(node, "operation", label),
                    self._read_ports(node["inputs"], f"{label}.inputs"),
                    self._read_ports(node["outputs"], f"{label}.outputs"),
                )
            )
        return tuple(nodes)

    def _read_edges(self, value: object) -> tuple[WorkflowEdge, ...]:
        items = self._require_list(value, "workflow.edges")
        edges: list[WorkflowEdge] = []
        for index, item in enumerate(items):
            label = f"workflow.edges[{index}]"
            edge = self._require_mapping(item, label)
            self._require_exact_keys(edge, _EDGE_KEYS, label)
            edges.append(
                WorkflowEdge(
                    self._read_endpoint(edge["source"], f"{label}.source", source=True),
                    self._read_endpoint(edge["target"], f"{label}.target", source=False),
                )
            )
        return tuple(edges)

    def _read_endpoint(self, value: object, label: str, *, source: bool) -> WorkflowEndpoint:
        endpoint = self._require_mapping(value, label)
        if set(endpoint) == _NODE_ENDPOINT_KEYS:
            return WorkflowEndpoint(
                WorkflowEndpointKind.NODE,
                self._require_string(endpoint, "port", label),
                self._require_string(endpoint, "node", label),
            )
        boundary_keys = _WORKFLOW_INPUT_ENDPOINT_KEYS if source else _WORKFLOW_OUTPUT_ENDPOINT_KEYS
        self._require_exact_keys(endpoint, boundary_keys, label)
        field = "workflow_input" if source else "workflow_output"
        kind = (
            WorkflowEndpointKind.WORKFLOW_INPUT if source else WorkflowEndpointKind.WORKFLOW_OUTPUT
        )
        return WorkflowEndpoint(kind, self._require_string(endpoint, field, label))

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return read_yaml(path)
        except yaml.YAMLError as exc:
            raise WorkflowError("Workflow manifest YAML is malformed.") from exc
        except (EngineeringError, OSError, TypeError, UnicodeError) as exc:
            raise WorkflowError(f"Workflow manifest could not be read: {exc}") from exc

    @classmethod
    def _reject_secret_content(cls, value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_text = str(key)
                path = f"{prefix}.{key_text}" if prefix else key_text
                normalized = key_text.lower().replace("-", "_")
                if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
                    raise WorkflowError(
                        f"Secret-like workflow manifest field is not allowed: {path}."
                    )
                cls._reject_secret_content(nested, path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                cls._reject_secret_content(nested, f"{prefix}[{index}]")
        elif isinstance(value, str) and any(
            pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS
        ):
            raise WorkflowError(f"Secret-like workflow manifest value is not allowed: {prefix}.")

    @staticmethod
    def _require_exact_keys(data: dict[str, Any], expected: frozenset[str], label: str) -> None:
        if not all(isinstance(key, str) for key in data):
            raise WorkflowError(f"{label} keys must be strings.")
        missing = sorted(expected - set(data))
        unexpected = sorted(set(data) - expected)
        if missing:
            raise WorkflowError(f"{label} is missing keys: {', '.join(missing)}.")
        if unexpected:
            raise WorkflowError(f"{label} contains unknown keys: {', '.join(unexpected)}.")

    @staticmethod
    def _require_mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise WorkflowError(f"{label} must be a mapping with string keys.")
        return value

    @staticmethod
    def _require_list(value: object, label: str) -> list[object]:
        if not isinstance(value, list):
            raise WorkflowError(f"{label} must be a list.")
        return value

    @staticmethod
    def _require_string(data: dict[str, Any], field: str, prefix: str) -> str:
        value = data[field]
        if not isinstance(value, str):
            raise WorkflowError(f"{prefix}.{field} must be a string.")
        return value

    @staticmethod
    def _require_integer(data: dict[str, Any], field: str, prefix: str) -> int:
        value = data[field]
        if type(value) is not int:
            raise WorkflowError(f"{prefix}.{field} must be an integer.")
        return value

    @staticmethod
    def _read_enum[T: StrEnum](enum_type: type[T], value: object, label: str) -> T:
        if not isinstance(value, str):
            raise WorkflowError(f"{label} must be a string.")
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise WorkflowError(f"{label} must be one of: {allowed}.") from exc
