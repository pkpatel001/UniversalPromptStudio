"""Repository contracts used by application services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from Backend.domain.models import Project, Prompt


class ProjectRepository(ABC):
    """Persistence contract for projects."""

    @abstractmethod
    def add(self, project: Project) -> None:
        """Persist a project."""

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        """Load a project by id."""


class PromptRepository(ABC):
    """Persistence contract for prompts."""

    @abstractmethod
    def add(self, prompt: Prompt) -> None:
        """Persist a prompt."""

    @abstractmethod
    def get(self, prompt_id: str) -> Prompt | None:
        """Load a prompt by id."""

    @abstractmethod
    def list(self) -> Sequence[Prompt]:
        """Return all prompts."""


class HistoryRepository(ABC):
    """Persistence contract for history entries."""


class TemplateRepository(ABC):
    """Persistence contract for templates."""


class CategoryRepository(ABC):
    """Persistence contract for categories."""


class SettingsRepository(ABC):
    """Persistence contract for settings."""


class TagRepository(ABC):
    """Persistence contract for tags."""

