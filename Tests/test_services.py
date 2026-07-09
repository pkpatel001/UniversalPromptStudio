from Backend.application.prompt_builder import PromptBuilder
from Backend.application.services import ProjectService, PromptService
from Backend.core.events import EventBus, EventNames
from Backend.domain.models import Prompt
from Backend.infrastructure.repositories.in_memory import (
    InMemoryProjectRepository,
    InMemoryPromptRepository,
)


def test_project_service_publishes_project_opened_event() -> None:
    received: list[str] = []
    event_bus = EventBus()
    event_bus.subscribe(EventNames.PROJECT_OPENED, lambda event: received.append(event.name))
    service = ProjectService(InMemoryProjectRepository(), event_bus)

    project = service.create_project("UPS")

    assert project.name == "UPS"
    assert received == [EventNames.PROJECT_OPENED]


def test_prompt_service_persists_prompt() -> None:
    repository = InMemoryPromptRepository()
    service = PromptService(repository, PromptBuilder(), EventBus())
    prompt = Prompt(title="Test")

    service.create_prompt(prompt)

    assert repository.get(prompt.prompt_id) == prompt

