"""E-016.5 bounded immutable workflow value tests."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from types import MappingProxyType

import pytest

from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    MAX_WORKFLOW_COLLECTION_ITEMS,
    MAX_WORKFLOW_STRING_CHARS,
    WorkflowPortValue,
    WorkflowRunRequest,
    WorkflowValueType,
    freeze_workflow_value,
    workflow_value_matches,
)


class _UnreadableMapping(Mapping[str, object]):
    def __getitem__(self, key: str) -> object:
        raise RuntimeError("sensitive mapping detail")

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError("sensitive mapping detail")

    def __len__(self) -> int:
        raise RuntimeError("sensitive mapping detail")


def test_freezes_nested_json_values_without_retaining_mutable_containers() -> None:
    source = {"zeta": [1, {"ready": True}], "alpha": "text"}

    frozen = freeze_workflow_value(source)

    assert isinstance(frozen, MappingProxyType)
    assert tuple(frozen) == ("alpha", "zeta")
    assert frozen["zeta"] == (1, {"ready": True})
    source["alpha"] = "changed"
    assert frozen["alpha"] == "text"
    with pytest.raises(TypeError):
        frozen["alpha"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    ("value", "message"),
    (
        (None, "null is not supported"),
        (float("inf"), "must be finite"),
        ("x" * (MAX_WORKFLOW_STRING_CHARS + 1), "at most"),
        ([0] * (MAX_WORKFLOW_COLLECTION_ITEMS + 1), "at most"),
        ({" untrimmed": "value"}, "trimmed text"),
    ),
    ids=(
        "null",
        "infinite",
        "oversized-string",
        "oversized-array",
        "untrimmed-key",
    ),
)
def test_rejects_unbounded_or_non_json_values(value: object, message: str) -> None:
    with pytest.raises(WorkflowError, match=message):
        freeze_workflow_value(value)


def test_rejects_cycles_and_excessive_depth() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    nested: object = "value"
    for _index in range(9):
        nested = [nested]

    with pytest.raises(WorkflowError, match="must not contain cycles"):
        freeze_workflow_value(cyclic)
    with pytest.raises(WorkflowError, match="nest at most"):
        freeze_workflow_value(nested)


def test_runtime_type_matching_distinguishes_boolean_integer_and_number() -> None:
    assert workflow_value_matches("text", WorkflowValueType.STRING)
    assert workflow_value_matches(1, WorkflowValueType.INTEGER)
    assert workflow_value_matches(1.5, WorkflowValueType.NUMBER)
    assert workflow_value_matches(True, WorkflowValueType.BOOLEAN)
    assert workflow_value_matches({"key": "value"}, WorkflowValueType.OBJECT)
    assert workflow_value_matches((1, 2), WorkflowValueType.ARRAY)
    assert not workflow_value_matches(True, WorkflowValueType.INTEGER)
    assert not workflow_value_matches(None, WorkflowValueType.OBJECT)


def test_request_rejects_duplicate_ports_and_aggregate_transport_overflow() -> None:
    with pytest.raises(WorkflowError, match="unique port ids"):
        WorkflowRunRequest(
            "run-1",
            (
                WorkflowPortValue("input", "one"),
                WorkflowPortValue("input", "two"),
            ),
        )

    many = tuple(
        WorkflowPortValue(f"p{index}", list(range(MAX_WORKFLOW_COLLECTION_ITEMS)))
        for index in range(17)
    )
    with pytest.raises(WorkflowError, match="total value nodes"):
        WorkflowRunRequest("run-2", many)


def test_contains_unexpected_custom_mapping_read_failures() -> None:
    with pytest.raises(WorkflowError, match="could not be read safely") as captured:
        WorkflowPortValue("input", _UnreadableMapping())

    assert "sensitive" not in str(captured.value)
