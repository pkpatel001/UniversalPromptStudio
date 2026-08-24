"""Bridge safe Engineering workflow lifecycle events to the application event bus."""

from __future__ import annotations

from Backend.core.events import DomainEvent, EventBus, EventNames
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowExecutionEvent,
    WorkflowExecutionEventKind,
)


class WorkflowEventBusSink:
    """Publish value-free workflow lifecycle metadata through Backend events."""

    def __init__(self, event_bus: EventBus) -> None:
        if not isinstance(event_bus, EventBus):
            raise WorkflowError("Workflow event bridge requires EventBus.")
        self._event_bus = event_bus

    def publish(self, event: WorkflowExecutionEvent) -> None:
        """Translate one bounded SDK event without exposing runtime values."""

        if not isinstance(event, WorkflowExecutionEvent):
            raise WorkflowError("Workflow event bridge requires WorkflowExecutionEvent.")
        event_name = (
            EventNames.WORKFLOW_STARTED
            if event.kind == WorkflowExecutionEventKind.STARTED
            else EventNames.WORKFLOW_COMPLETED
        )
        payload: dict[str, object] = {
            "run_id": event.run_id,
            "workflow_id": event.workflow_id.value,
            "workflow_version": event.version.value,
            "completed_steps": event.completed_steps,
        }
        if event.kind == WorkflowExecutionEventKind.COMPLETED:
            payload["succeeded"] = event.succeeded
            payload["failure_code"] = (
                event.failure_code.value if event.failure_code is not None else None
            )
        self._event_bus.publish(DomainEvent(event_name, payload))


__all__ = ["WorkflowEventBusSink"]
