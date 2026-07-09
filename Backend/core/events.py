"""Domain event definitions and a synchronous event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base event emitted by the core application."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """In-process event bus used by services and future plugins."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for an event name."""

        self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""

        for handler in list(self._handlers.get(event.name, [])):
            handler(event)


class EventNames:
    """Canonical event names shared across services and plugins."""

    PROJECT_OPENED = "ProjectOpened"
    PROJECT_CLOSED = "ProjectClosed"
    PROMPT_CREATED = "PromptCreated"
    PROMPT_UPDATED = "PromptUpdated"
    PROMPT_EXECUTED = "PromptExecuted"
    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    PLUGIN_LOADED = "PluginLoaded"
    PLUGIN_UNLOADED = "PluginUnloaded"
    SETTINGS_CHANGED = "SettingsChanged"
    HISTORY_RECORDED = "HistoryRecorded"

