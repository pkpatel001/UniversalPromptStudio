from Backend.application.services import PromptExecutionService
from Backend.core.events import EventBus
from Backend.core.registry import ProviderRegistry
from Backend.domain.models import PromptExecutionRequest
from Backend.implementations.dummy import (
    BasicPromptValidator,
    DummyAIProvider,
    InMemoryHistoryProvider,
    NoOpPromptOptimizer,
)
from Backend.interfaces.providers import AIProvider


def test_execution_service_uses_registered_provider_and_records_history() -> None:
    registry: ProviderRegistry[AIProvider] = ProviderRegistry()
    registry.register("dummy", DummyAIProvider())
    history = InMemoryHistoryProvider()
    service = PromptExecutionService(
        ai_providers=registry,
        validator=BasicPromptValidator(),
        optimizer=NoOpPromptOptimizer(),
        history_provider=history,
        event_bus=EventBus(),
    )

    result = service.execute(PromptExecutionRequest(prompt="Hello", provider_name="dummy"))

    assert result.output == "[dummy response]\nHello"
    assert len(history.entries) == 1

