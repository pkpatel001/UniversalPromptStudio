"""In-memory repositories used for tests and early development."""

from __future__ import annotations

from Backend.domain.models import Project, Prompt
from Backend.repositories.contracts import ProjectRepository, PromptRepository


class InMemoryProjectRepository(ProjectRepository):
    """In-memory project repository."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def add(self, project: Project) -> None:
        """Persist a project."""

        self._projects[project.project_id] = project

    def get(self, project_id: str) -> Project | None:
        """Load a project by id."""

        return self._projects.get(project_id)


class InMemoryPromptRepository(PromptRepository):
    """In-memory prompt repository."""

    def __init__(self) -> None:
        self._prompts: dict[str, Prompt] = {}

    def add(self, prompt: Prompt) -> None:
        """Persist a prompt."""

        self._prompts[prompt.prompt_id] = prompt

    def get(self, prompt_id: str) -> Prompt | None:
        """Load a prompt by id."""

        return self._prompts.get(prompt_id)

    def list(self) -> list[Prompt]:
        """Return all prompts."""

        return list(self._prompts.values())

