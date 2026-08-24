"""E-016.5 offline workflow application integration tests."""

from __future__ import annotations

import importlib
import socket
import subprocess

import pytest

from Backend.core.container import create_in_memory_container
from Backend.core.events import EventNames
from Backend.implementations.dummy import SequentialWorkflowEngine
from Engineering.WorkflowSystem import (
    WorkflowPortValue,
    WorkflowRunRequest,
    WorkflowRunSuccess,
)


def test_container_exposes_explicit_offline_workflow_runtime_and_plan() -> None:
    container = create_in_memory_container()

    assert tuple(
        item.operation_id for item in container.workflow_operation_registry.registrations
    ) == ("ups.echo-text", "ups.uppercase-text")
    assert container.offline_workflow_plan.workflow_id == "ups.offline-text-flow"
    assert tuple(step.node.node_id for step in container.offline_workflow_plan.steps) == (
        "echo",
        "uppercase",
    )


def test_reference_workflow_executes_offline_and_publishes_safe_existing_events() -> None:
    container = create_in_memory_container()
    events = []
    container.event_bus.subscribe(EventNames.WORKFLOW_STARTED, events.append)
    container.event_bus.subscribe(EventNames.WORKFLOW_COMPLETED, events.append)

    outcome = container.workflow_execution_service.execute(
        container.offline_workflow_plan,
        WorkflowRunRequest(
            "integrated-run",
            (WorkflowPortValue("input", "Integrated"),),
        ),
    )

    assert isinstance(outcome, WorkflowRunSuccess)
    assert outcome.outputs == (WorkflowPortValue("output", "INTEGRATED"),)
    assert tuple(event.name for event in events) == (
        EventNames.WORKFLOW_STARTED,
        EventNames.WORKFLOW_COMPLETED,
    )
    assert events[0].payload == {
        "run_id": "integrated-run",
        "workflow_id": "ups.offline-text-flow",
        "workflow_version": "1.0.0",
        "completed_steps": 0,
    }
    assert events[1].payload == {
        "run_id": "integrated-run",
        "workflow_id": "ups.offline-text-flow",
        "workflow_version": "1.0.0",
        "completed_steps": 2,
        "succeeded": True,
        "failure_code": None,
    }
    assert "Integrated" not in repr(events)


def test_reference_workflow_uses_no_import_network_or_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = create_in_memory_container()
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda *_args, **_kwargs: pytest.fail("dynamic import attempted"),
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

    outcome = container.workflow_execution_service.execute(
        container.offline_workflow_plan,
        WorkflowRunRequest(
            "offline-run",
            (WorkflowPortValue("input", "safe"),),
        ),
    )

    assert isinstance(outcome, WorkflowRunSuccess)
    assert outcome.outputs == (WorkflowPortValue("output", "SAFE"),)


def test_legacy_placeholder_engine_remains_unchanged() -> None:
    assert SequentialWorkflowEngine().run(("first", "second")) == [
        "first",
        "second",
    ]
