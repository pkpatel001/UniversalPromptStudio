from pathlib import Path

from Backend.core.container import create_in_memory_container, create_sqlite_container
from Backend.domain.models import PromptExecutionRequest


def test_in_memory_container_wires_dummy_execution() -> None:
    container = create_in_memory_container()

    result = container.prompt_execution_service.execute(
        PromptExecutionRequest(prompt="Build safely", provider_name="dummy")
    )

    assert result.output == "[dummy response]\nBuild safely"


def test_sqlite_container_wires_persistent_services(tmp_path: Path) -> None:
    container = create_sqlite_container(tmp_path / "ups.db")

    project = container.project_service.create_project("UPS")
    loaded = container.project_repository.get(project.project_id)

    assert loaded == project
