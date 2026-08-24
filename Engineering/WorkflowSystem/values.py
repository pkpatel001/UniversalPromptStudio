"""Deeply immutable, bounded values for controlled workflow transport."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from Engineering.core.exceptions import WorkflowError

from .models import WorkflowValueType
from .validation import require_local_id

MAX_WORKFLOW_VALUE_DEPTH = 8
MAX_WORKFLOW_COLLECTION_ITEMS = 256
MAX_WORKFLOW_OBJECT_KEY_CHARS = 128
MAX_WORKFLOW_STRING_CHARS = 65_536
MAX_WORKFLOW_TRANSPORT_NODES = 4_096


@dataclass(frozen=True, slots=True)
class WorkflowPortValue:
    """One named, deeply frozen JSON-shaped runtime value."""

    port_id: str
    value: object

    def __post_init__(self) -> None:
        require_local_id(self.port_id, "Workflow runtime port id")
        object.__setattr__(self, "value", freeze_workflow_value(self.value))


def freeze_workflow_value(value: object) -> object:
    """Copy one JSON-shaped value into bounded immutable containers."""

    try:
        return _freeze(
            value,
            depth=0,
            budget=[MAX_WORKFLOW_TRANSPORT_NODES],
            active=set(),
        )
    except WorkflowError:
        raise
    except Exception as exc:
        raise WorkflowError("Workflow runtime value could not be read safely.") from exc


def workflow_value_weight(value: object) -> int:
    """Count scalar and collection nodes in an already frozen value."""

    if isinstance(value, Mapping):
        return 1 + sum(workflow_value_weight(item) for item in value.values())
    if isinstance(value, tuple):
        return 1 + sum(workflow_value_weight(item) for item in value)
    return 1


def workflow_value_matches(value: object, value_type: WorkflowValueType) -> bool:
    """Return whether one frozen value matches one declared schema-1 port type."""

    if value_type == WorkflowValueType.STRING:
        return isinstance(value, str)
    if value_type == WorkflowValueType.INTEGER:
        return type(value) is int
    if value_type == WorkflowValueType.NUMBER:
        return type(value) in {int, float}
    if value_type == WorkflowValueType.BOOLEAN:
        return type(value) is bool
    if value_type == WorkflowValueType.OBJECT:
        return isinstance(value, Mapping)
    if value_type == WorkflowValueType.ARRAY:
        return isinstance(value, tuple)
    return False


def _freeze(
    value: object,
    *,
    depth: int,
    budget: list[int],
    active: set[int],
) -> object:
    budget[0] -= 1
    if budget[0] < 0:
        raise WorkflowError(
            f"Workflow runtime value exceeds {MAX_WORKFLOW_TRANSPORT_NODES} total nodes."
        )
    if isinstance(value, str):
        if len(value) > MAX_WORKFLOW_STRING_CHARS:
            raise WorkflowError(
                f"Workflow runtime strings may contain at most "
                f"{MAX_WORKFLOW_STRING_CHARS} characters."
            )
        return value
    if type(value) is bool:
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise WorkflowError("Workflow runtime numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        _require_collection_depth(depth)
        if len(value) > MAX_WORKFLOW_COLLECTION_ITEMS:
            raise WorkflowError(
                f"Workflow runtime objects may contain at most "
                f"{MAX_WORKFLOW_COLLECTION_ITEMS} entries."
            )
        identity = id(value)
        if identity in active:
            raise WorkflowError("Workflow runtime values must not contain cycles.")
        active.add(identity)
        try:
            items = list(value.items())
            if not all(isinstance(key, str) for key, _nested in items):
                raise WorkflowError("Workflow runtime object keys must be strings.")
            for key, _nested in items:
                if not key or key != key.strip() or len(key) > MAX_WORKFLOW_OBJECT_KEY_CHARS:
                    raise WorkflowError(
                        f"Workflow runtime object keys must be non-empty, trimmed "
                        f"text of at most {MAX_WORKFLOW_OBJECT_KEY_CHARS} characters."
                    )
            frozen = {
                key: _freeze(
                    nested,
                    depth=depth + 1,
                    budget=budget,
                    active=active,
                )
                for key, nested in sorted(items, key=lambda item: item[0])
            }
        finally:
            active.remove(identity)
        return MappingProxyType(frozen)
    if isinstance(value, list | tuple):
        _require_collection_depth(depth)
        if len(value) > MAX_WORKFLOW_COLLECTION_ITEMS:
            raise WorkflowError(
                f"Workflow runtime arrays may contain at most "
                f"{MAX_WORKFLOW_COLLECTION_ITEMS} items."
            )
        identity = id(value)
        if identity in active:
            raise WorkflowError("Workflow runtime values must not contain cycles.")
        active.add(identity)
        try:
            return tuple(
                _freeze(
                    nested,
                    depth=depth + 1,
                    budget=budget,
                    active=active,
                )
                for nested in value
            )
        finally:
            active.remove(identity)
    raise WorkflowError(
        "Workflow runtime values must be JSON-shaped strings, finite numbers, "
        "booleans, objects, or arrays; null is not supported."
    )


def _require_collection_depth(depth: int) -> None:
    if depth >= MAX_WORKFLOW_VALUE_DEPTH:
        raise WorkflowError(
            f"Workflow runtime values may nest at most "
            f"{MAX_WORKFLOW_VALUE_DEPTH} collection levels."
        )


__all__ = [
    "MAX_WORKFLOW_COLLECTION_ITEMS",
    "MAX_WORKFLOW_OBJECT_KEY_CHARS",
    "MAX_WORKFLOW_STRING_CHARS",
    "MAX_WORKFLOW_TRANSPORT_NODES",
    "MAX_WORKFLOW_VALUE_DEPTH",
    "WorkflowPortValue",
    "freeze_workflow_value",
    "workflow_value_matches",
    "workflow_value_weight",
]
