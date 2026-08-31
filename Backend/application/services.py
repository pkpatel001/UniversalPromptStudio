"""Application services exposed to the presentation layer."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from Backend.application.prompt_builder import PromptBuilder
from Backend.core.events import DomainEvent, EventBus, EventNames
from Backend.core.registry import ProviderRegistry
from Backend.domain.models import (
    Project,
    Prompt,
    PromptBlock,
    PromptExecutionRequest,
    PromptExecutionResult,
)
from Backend.interfaces.providers import (
    AIProvider,
    HistoryProvider,
    PromptOptimizer,
    PromptValidator,
    SearchProvider,
)
from Backend.repositories.contracts import ProjectRepository, PromptRepository

MAX_CATEGORY_LENGTH = 80
MAX_TAGS = 10
MAX_TAG_LENGTH = 32
MAX_BLOCKS = 12
MAX_BLOCK_CONTENT_LENGTH = 2_000
MAX_TOTAL_BLOCK_CONTENT_LENGTH = 12_000
MAX_SEARCH_QUERY_LENGTH = 120


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

    def delete_project(self, project_id: str) -> int:
        """Delete a project and its dependent prompts."""

        deleted_prompt_count = self._repository.delete(project_id)
        if deleted_prompt_count is None:
            raise LookupError("Project does not exist.")
        self._event_bus.publish(
            DomainEvent(
                EventNames.PROJECT_CLOSED,
                {"project_id": project_id, "deleted_prompt_count": deleted_prompt_count},
            )
        )
        return deleted_prompt_count


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

    def get_project_prompt(self, project_id: str, prompt_id: str) -> Prompt:
        """Load one prompt only within its owning project."""

        self._require_project(project_id)
        prompt = self._repository.get(prompt_id)
        if prompt is None or prompt.project_id != project_id:
            raise LookupError("Prompt does not exist in this project.")
        return prompt

    def update_library_prompt(
        self,
        project_id: str,
        prompt_id: str,
        title: str,
        category: str | None,
        tags: Sequence[str],
        blocks: Sequence[PromptBlock],
    ) -> Prompt:
        """Validate and durably replace editable prompt content."""

        prompt = self.get_project_prompt(project_id, prompt_id)
        prompt.title = _bounded_text(title, 120, "Prompt title")
        prompt.category = _optional_bounded_text(category, MAX_CATEGORY_LENGTH, "Prompt category")
        prompt.tags = _normalize_tags(tags)
        prompt.blocks = _normalize_blocks(blocks)
        prompt.updated_at = datetime.now(UTC)
        self._repository.add(prompt)
        self._event_bus.publish(
            DomainEvent(EventNames.PROMPT_UPDATED, {"prompt_id": prompt.prompt_id})
        )
        return prompt

    def delete_library_prompt(self, project_id: str, prompt_id: str) -> None:
        """Delete one prompt only within its owning project."""

        self._require_project(project_id)
        if not self._repository.delete(prompt_id, project_id):
            raise LookupError("Prompt does not exist in this project.")
        self._event_bus.publish(DomainEvent(EventNames.PROMPT_DELETED, {"prompt_id": prompt_id}))

    def search_project_prompts(self, project_id: str, query: str) -> list[Prompt]:
        """Search deterministic local prompt text within one project."""

        self._require_project(project_id)
        normalized_query = _bounded_text(query, MAX_SEARCH_QUERY_LENGTH, "Search query")
        needle = normalized_query.casefold()
        return [
            prompt
            for prompt in self._repository.list(project_id)
            if needle in _prompt_search_text(prompt)
        ]

    def _require_project(self, project_id: str) -> None:
        if self._project_repository is None or self._project_repository.get(project_id) is None:
            raise LookupError("Project does not exist.")

    def render_prompt(self, prompt: Prompt) -> str:
        """Build the final prompt text."""

        return self._prompt_builder.build(prompt)


def _bounded_text(value: str, maximum: int, label: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters.")
    return normalized


def _optional_bounded_text(value: str | None, maximum: int, label: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{label} must not exceed {maximum} characters.")
    return normalized


def _normalize_tags(tags: Sequence[str]) -> set[str]:
    if isinstance(tags, str) or len(tags) > MAX_TAGS:
        raise ValueError(f"A prompt supports at most {MAX_TAGS} tags.")
    normalized: dict[str, str] = {}
    for tag in tags:
        value = _bounded_text(tag, MAX_TAG_LENGTH, "Prompt tag")
        if "\n" in value or "\r" in value:
            raise ValueError("Prompt tags must be single-line text.")
        key = value.casefold()
        if key in normalized:
            raise ValueError("Prompt tags must be unique ignoring case.")
        normalized[key] = value
    return set(normalized.values())


def _normalize_blocks(blocks: Sequence[PromptBlock]) -> list[PromptBlock]:
    if len(blocks) > MAX_BLOCKS:
        raise ValueError(f"A prompt supports at most {MAX_BLOCKS} blocks.")
    normalized: list[PromptBlock] = []
    total_content = 0
    for order, block in enumerate(blocks):
        content = _bounded_text(block.content, MAX_BLOCK_CONTENT_LENGTH, "Prompt block content")
        total_content += len(content)
        normalized.append(
            PromptBlock(
                block_type=block.block_type,
                content=content,
                order=order,
                enabled=block.enabled,
            )
        )
    if total_content > MAX_TOTAL_BLOCK_CONTENT_LENGTH:
        raise ValueError(
            f"Prompt block content must not exceed {MAX_TOTAL_BLOCK_CONTENT_LENGTH} characters."
        )
    return normalized


def _prompt_search_text(prompt: Prompt) -> str:
    values = [prompt.title, prompt.category or "", *sorted(prompt.tags, key=str.casefold)]
    values.extend(block.content for block in sorted(prompt.blocks, key=lambda item: item.order))
    return "\n".join(values).casefold()


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
