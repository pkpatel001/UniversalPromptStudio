from pathlib import Path

from Backend.domain.models import Project, Prompt, PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import (
    SQLiteProjectRepository,
    SQLitePromptRepository,
    SQLiteStorageProvider,
)


def create_storage(database_path: Path) -> SQLiteStorageProvider:
    storage = SQLiteStorageProvider(database_path)
    storage.initialize()
    return storage


def test_sqlite_project_repository_persists_project(tmp_path: Path) -> None:
    storage = create_storage(tmp_path / "ups.db")
    repository = SQLiteProjectRepository(storage)
    project = Project(name="Universal Prompt Studio", description="Offline prompt workspace")

    repository.add(project)
    loaded = repository.get(project.project_id)

    assert loaded == project


def test_sqlite_prompt_repository_persists_blocks_and_tags(tmp_path: Path) -> None:
    storage = create_storage(tmp_path / "ups.db")
    repository = SQLitePromptRepository(storage)
    prompt = Prompt(
        title="Architecture Builder",
        category="Prompt Engineering",
        tags={"architecture", "offline"},
        blocks=[
            PromptBlock(PromptBlockType.GOAL, "Create a durable architecture.", order=2),
            PromptBlock(PromptBlockType.ROLE, "Principal engineer", order=1),
        ],
    )

    repository.add(prompt)
    loaded = repository.get(prompt.prompt_id)

    assert loaded is not None
    assert loaded.prompt_id == prompt.prompt_id
    assert loaded.title == prompt.title
    assert loaded.category == prompt.category
    assert loaded.tags == prompt.tags
    assert loaded.created_at == prompt.created_at
    assert loaded.updated_at == prompt.updated_at
    assert [block.block_type for block in loaded.blocks] == [
        PromptBlockType.ROLE,
        PromptBlockType.GOAL,
    ]


def test_sqlite_prompt_repository_lists_prompts_by_title(tmp_path: Path) -> None:
    storage = create_storage(tmp_path / "ups.db")
    repository = SQLitePromptRepository(storage)
    repository.add(Prompt(title="Zebra"))
    repository.add(Prompt(title="Alpha"))

    prompts = repository.list()

    assert [prompt.title for prompt in prompts] == ["Alpha", "Zebra"]


def test_sqlite_prompt_repository_replaces_existing_prompt(tmp_path: Path) -> None:
    storage = create_storage(tmp_path / "ups.db")
    repository = SQLitePromptRepository(storage)
    prompt = Prompt(
        title="Original",
        blocks=[PromptBlock(PromptBlockType.ROLE, "Draft", order=1)],
    )
    repository.add(prompt)
    prompt.title = "Updated"
    prompt.blocks = [PromptBlock(PromptBlockType.GOAL, "Ship phase one.", order=1)]

    repository.add(prompt)
    loaded = repository.get(prompt.prompt_id)

    assert loaded is not None
    assert loaded.title == "Updated"
    assert loaded.blocks == [PromptBlock(PromptBlockType.GOAL, "Ship phase one.", order=1)]
