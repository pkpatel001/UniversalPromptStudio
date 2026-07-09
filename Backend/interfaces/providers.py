"""Provider and service interfaces for extensible subsystems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from Backend.domain.models import Prompt, PromptExecutionRequest, PromptExecutionResult


class AIProvider(ABC):
    """Contract implemented by local or remote AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    def execute(self, request: PromptExecutionRequest) -> PromptExecutionResult:
        """Execute a prompt and return the provider response."""


class PromptExecutor(ABC):
    """Contract for prompt execution orchestration."""

    @abstractmethod
    def execute(self, request: PromptExecutionRequest) -> PromptExecutionResult:
        """Execute a prompt."""


class PromptOptimizer(ABC):
    """Contract for prompt optimization strategies."""

    @abstractmethod
    def optimize(self, prompt: str) -> str:
        """Return an optimized prompt."""


class PromptValidator(ABC):
    """Contract for prompt validation."""

    @abstractmethod
    def validate(self, prompt: str) -> list[str]:
        """Return validation errors. Empty means valid."""


class StorageProvider(ABC):
    """Contract for persistence providers."""

    @abstractmethod
    def initialize(self) -> None:
        """Prepare storage resources."""


class TemplateProvider(ABC):
    """Contract for template providers."""

    @abstractmethod
    def list_templates(self) -> Sequence[str]:
        """Return available template names."""


class WorkflowEngine(ABC):
    """Contract for workflow engines."""

    @abstractmethod
    def run(self, steps: Sequence[str]) -> list[str]:
        """Run workflow steps and return step outputs."""


class ExportProvider(ABC):
    """Contract for export providers."""

    @abstractmethod
    def export(self, prompt: Prompt) -> bytes:
        """Export a prompt into a serialized format."""


class Plugin(ABC):
    """Contract implemented by dynamically loaded plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin name."""

    @abstractmethod
    def activate(self, registry: Any) -> None:
        """Activate the plugin and register contributions."""


class SearchProvider(ABC):
    """Contract for interchangeable search providers."""

    @abstractmethod
    def index_prompt(self, prompt: Prompt) -> None:
        """Index or update a prompt."""

    @abstractmethod
    def search(self, query: str) -> list[Prompt]:
        """Search prompts."""


class EmbeddingProvider(ABC):
    """Contract for vector embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return an embedding vector."""


class HistoryProvider(ABC):
    """Contract for execution history providers."""

    @abstractmethod
    def record(self, request: PromptExecutionRequest, result: PromptExecutionResult) -> None:
        """Record execution history."""


class SettingsProvider(ABC):
    """Contract for application settings providers."""

    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """Return a setting value."""

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Persist a setting value."""

