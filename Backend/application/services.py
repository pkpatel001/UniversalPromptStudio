"""Application services exposed to the presentation layer."""

from __future__ import annotations

from Backend.application.prompt_builder import PromptBuilder
from Backend.core.events import DomainEvent, EventBus, EventNames
from Backend.core.registry import ProviderRegistry
from Backend.domain.models import Project, Prompt, PromptExecutionRequest, PromptExecutionResult
from Backend.interfaces.providers import (
    AIProvider,
    HistoryProvider,
    PromptOptimizer,
    PromptValidator,
    SearchProvider,
)
from Backend.repositories.contracts import ProjectRepository, PromptRepository


class ProjectService:
    """Coordinates project use cases."""

    def __init__(self, repository: ProjectRepository, event_bus: EventBus) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def create_project(self, name: str, description: str = "") -> Project:
        """Create and persist a project."""

        normalized_name = name.strip()
        normalized_description = description.strip()
        if not normalized_name or len(normalized_name) > 120:
            raise ValueError("Project name must contain 1 to 120 characters.")
        if len(normalized_description) > 1_000:
            raise ValueError("Project description must not exceed 1000 characters.")
        project = Project(name=normalized_name, description=normalized_description)
        self._repository.add(project)
        self._event_bus.publish(
            DomainEvent(EventNames.PROJECT_OPENED, {"project_id": project.project_id})
        )
        return project

    def list_projects(self) -> list[Project]:
        """Return the durable project library."""

        return list(self._repository.list())


class PromptService:
    """Coordinates prompt authoring use cases."""

    def __init__(
        self,
        repository: PromptRepository,
        prompt_builder: PromptBuilder,
        event_bus: EventBus,
        project_repository: ProjectRepository | None = None,
    ) -> None:
        self._repository = repository
        self._prompt_builder = prompt_builder
        self._event_bus = event_bus
        self._project_repository = project_repository

    def create_prompt(self, prompt: Prompt) -> Prompt:
        """Persist a prompt and publish an event."""

        self._repository.add(prompt)
        self._event_bus.publish(
            DomainEvent(EventNames.PROMPT_CREATED, {"prompt_id": prompt.prompt_id})
        )
        return prompt

    def create_library_prompt(self, project_id: str, title: str) -> Prompt:
        """Create the minimal project-owned prompt supported by A-002.1."""

        normalized_title = title.strip()
        if not normalized_title or len(normalized_title) > 120:
            raise ValueError("Prompt title must contain 1 to 120 characters.")
        if self._project_repository is None or self._project_repository.get(project_id) is None:
            raise LookupError("Project does not exist.")
        prompt = Prompt(title=normalized_title, project_id=project_id)
        return self.create_prompt(prompt)

    def list_project_prompts(self, project_id: str) -> list[Prompt]:
        """Return prompts owned by one project."""

        if self._project_repository is None or self._project_repository.get(project_id) is None:
            raise LookupError("Project does not exist.")
        return list(self._repository.list(project_id))

    def render_prompt(self, prompt: Prompt) -> str:
        """Build the final prompt text."""

        return self._prompt_builder.build(prompt)


class PromptExecutionService:
    """Coordinates validation, optimization, provider execution, and history."""

    def __init__(
        self,
        ai_providers: ProviderRegistry[AIProvider],
        validator: PromptValidator,
        optimizer: PromptOptimizer,
        history_provider: HistoryProvider,
        event_bus: EventBus,
    ) -> None:
        self._ai_providers = ai_providers
        self._validator = validator
        self._optimizer = optimizer
        self._history_provider = history_provider
        self._event_bus = event_bus

    def execute(self, request: PromptExecutionRequest) -> PromptExecutionResult:
        """Validate, optimize, and execute a prompt through the selected provider."""

        errors = self._validator.validate(request.prompt)
        if errors:
            raise ValueError("; ".join(errors))

        optimized_prompt = self._optimizer.optimize(request.prompt)
        provider = self._ai_providers.get(request.provider_name)
        optimized_request = PromptExecutionRequest(
            prompt=optimized_prompt,
            provider_name=request.provider_name,
            parameters=request.parameters,
        )
        result = provider.execute(optimized_request)
        self._history_provider.record(optimized_request, result)
        self._event_bus.publish(
            DomainEvent(EventNames.PROMPT_EXECUTED, {"provider": provider.name})
        )
        self._event_bus.publish(
            DomainEvent(EventNames.HISTORY_RECORDED, {"provider": provider.name})
        )
        return result


class SearchService:
    """Coordinates prompt indexing and search use cases."""

    def __init__(self, search_provider: SearchProvider) -> None:
        self._search_provider = search_provider

    def index_prompt(self, prompt: Prompt) -> None:
        """Index or update a prompt."""

        self._search_provider.index_prompt(prompt)

    def search(self, query: str) -> list[Prompt]:
        """Search indexed prompts."""

        return self._search_provider.search(query)
