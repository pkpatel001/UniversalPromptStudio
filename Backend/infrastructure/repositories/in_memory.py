"""In-memory repositories used for tests and early development."""

from __future__ import annotations

from Backend.domain.models import Project, Prompt
from Backend.repositories.contracts import ProjectRepository, PromptRepository


class InMemoryProjectRepository(ProjectRepository):
    """In-memory project repository."""

    def __init__(self, prompt_repository: InMemoryPromptRepository | None = None) -> None:
        self._projects: dict[str, Project] = {}
        self._prompt_repository = prompt_repository

    def add(self, project: Project) -> None:
        """Persist a project."""

        self._projects[project.project_id] = project

    def get(self, project_id: str) -> Project | None:
        """Load a project by id."""

        return self._projects.get(project_id)

    def list(self) -> list[Project]:
        """Return projects ordered by name and stable identifier."""

        return sorted(
            self._projects.values(),
            key=lambda project: (project.name.casefold(), project.project_id),
        )

    def delete(self, project_id: str) -> int | None:
        """Delete a project and all dependent prompts."""

        if project_id not in self._projects:
            return None
        dependent_count = 0
        if self._prompt_repository is not None:
            dependent_count = self._prompt_repository.delete_for_project(project_id)
        del self._projects[project_id]
        return dependent_count


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

    def list(self, project_id: str | None = None) -> list[Prompt]:
        """Return prompts, optionally restricted to one project."""

        prompts = [
            prompt
            for prompt in self._prompts.values()
            if project_id is None or prompt.project_id == project_id
        ]
        return sorted(prompts, key=lambda prompt: (prompt.title.casefold(), prompt.prompt_id))

    def delete(self, prompt_id: str, project_id: str) -> bool:
        """Delete one prompt only when its ownership matches."""

        prompt = self._prompts.get(prompt_id)
        if prompt is None or prompt.project_id != project_id:
            return False
        del self._prompts[prompt_id]
        return True

    def delete_for_project(self, project_id: str) -> int:
        """Delete all prompts owned by one project."""

        prompt_ids = [
            prompt_id
            for prompt_id, prompt in self._prompts.items()
            if prompt.project_id == project_id
        ]
        for prompt_id in prompt_ids:
            del self._prompts[prompt_id]
        return len(prompt_ids)
