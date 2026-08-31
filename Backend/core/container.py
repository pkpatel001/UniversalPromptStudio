"""Application composition root for dependency injection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from Backend.application.prompt_builder import PromptBuilder
from Backend.application.services import (
    ProjectService,
    PromptExecutionService,
    PromptService,
    SavedPromptRuntimeService,
    SearchService,
)
from Backend.core.events import EventBus
from Backend.core.registry import ProviderRegistry
from Backend.implementations.dummy import (
    BasicPromptValidator,
    BasicSearchProvider,
    DummyAIProvider,
    InMemoryHistoryProvider,
    NoOpPromptOptimizer,
)
from Backend.infrastructure.providers import ProviderRuntimeAIAdapter
from Backend.infrastructure.repositories.in_memory import (
    InMemoryProjectRepository,
    InMemoryPromptRepository,
)
from Backend.infrastructure.repositories.sqlite import (
    DATABASE_FILE_NAME,
    DatabaseUnavailableError,
    SQLiteProjectRepository,
    SQLitePromptRepository,
    SQLiteStorageProvider,
)
from Backend.infrastructure.workflows import WorkflowEventBusSink
from Backend.interfaces.providers import AIProvider
from Backend.repositories.contracts import ProjectRepository, PromptRepository
from Engineering.ProviderSystem import (
    OfflineEchoProvider,
    ProviderExecutionService,
    ProviderRuntimeRegistry,
    offline_echo_provider_record,
)
from Engineering.WorkflowSystem import (
    WorkflowExecutionPlan,
    WorkflowExecutionService,
    WorkflowOperationRegistry,
    offline_text_workflow_plan,
    register_offline_workflow_handlers,
)

DESKTOP_APP_DATA_ENV = "UPS_APP_DATA_DIR"


@dataclass(frozen=True)
class ApplicationContainer:
    """Resolved application dependencies exposed to presentation adapters."""

    event_bus: EventBus
    ai_providers: ProviderRegistry[AIProvider]
    workflow_operation_registry: WorkflowOperationRegistry
    workflow_execution_service: WorkflowExecutionService
    offline_workflow_plan: WorkflowExecutionPlan
    provider_runtime_registry: ProviderRuntimeRegistry
    project_repository: ProjectRepository
    prompt_repository: PromptRepository
    project_service: ProjectService
    prompt_service: PromptService
    prompt_execution_service: PromptExecutionService
    saved_prompt_runtime_service: SavedPromptRuntimeService
    search_service: SearchService


def create_in_memory_container() -> ApplicationContainer:
    """Create a container backed by in-memory repositories."""

    prompt_repository = InMemoryPromptRepository()
    return _create_container(
        project_repository=InMemoryProjectRepository(prompt_repository),
        prompt_repository=prompt_repository,
    )


def create_desktop_container() -> ApplicationContainer:
    """Create the installed application container in Tauri-owned app data."""

    configured = os.environ.get(DESKTOP_APP_DATA_ENV)
    if configured is None or not configured.strip():
        raise DatabaseUnavailableError("The application data directory is unavailable.")
    app_data_directory = Path(configured)
    if not app_data_directory.is_absolute():
        raise DatabaseUnavailableError("The application data directory is invalid.")
    return create_sqlite_container(app_data_directory / DATABASE_FILE_NAME)


def create_sqlite_container(database_path: Path) -> ApplicationContainer:
    """Create a container backed by SQLite repositories."""

    storage_provider = SQLiteStorageProvider(database_path)
    storage_provider.initialize()
    return _create_container(
        project_repository=SQLiteProjectRepository(storage_provider),
        prompt_repository=SQLitePromptRepository(storage_provider),
    )


def _create_container(
    project_repository: ProjectRepository,
    prompt_repository: PromptRepository,
) -> ApplicationContainer:
    """Wire core application dependencies."""

    event_bus = EventBus()
    ai_providers: ProviderRegistry[AIProvider] = ProviderRegistry()
    ai_providers.register("dummy", DummyAIProvider())
    provider_runtime_registry = ProviderRuntimeRegistry()
    offline_provider = OfflineEchoProvider()
    provider_runtime_registry.register(
        offline_echo_provider_record(),
        offline_provider,
    )
    offline_adapter = ProviderRuntimeAIAdapter(
        ProviderExecutionService(provider_runtime_registry),
        offline_provider.provider_id.value,
        offline_provider.version.value,
    )
    ai_providers.register(offline_adapter.name, offline_adapter)
    workflow_operation_registry = WorkflowOperationRegistry()
    register_offline_workflow_handlers(workflow_operation_registry)
    offline_workflow_plan = offline_text_workflow_plan(workflow_operation_registry)
    workflow_execution_service = WorkflowExecutionService(WorkflowEventBusSink(event_bus))
    prompt_builder = PromptBuilder()
    history_provider = InMemoryHistoryProvider()
    search_provider = BasicSearchProvider()
    project_service = ProjectService(project_repository, event_bus)
    prompt_service = PromptService(
        prompt_repository,
        prompt_builder,
        event_bus,
        project_repository,
    )
    prompt_execution_service = PromptExecutionService(
        ai_providers=ai_providers,
        validator=BasicPromptValidator(),
        optimizer=NoOpPromptOptimizer(),
        history_provider=history_provider,
        event_bus=event_bus,
    )


    return ApplicationContainer(
        event_bus=event_bus,
        ai_providers=ai_providers,
        provider_runtime_registry=provider_runtime_registry,
        workflow_operation_registry=workflow_operation_registry,
        workflow_execution_service=workflow_execution_service,
        offline_workflow_plan=offline_workflow_plan,
        project_repository=project_repository,
        prompt_repository=prompt_repository,
        project_service=project_service,
        prompt_service=prompt_service,
        prompt_execution_service=prompt_execution_service,
        saved_prompt_runtime_service=SavedPromptRuntimeService(
            prompt_service, prompt_execution_service
        ),
        search_service=SearchService(search_provider),
    )
