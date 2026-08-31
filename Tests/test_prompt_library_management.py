"""A-002.2 prompt editing, organization, search, and deletion tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from Backend.core.container import create_in_memory_container, create_sqlite_container
from Backend.domain.models import PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import CURRENT_SCHEMA_VERSION, DATABASE_FILE_NAME


def _blocks() -> list[PromptBlock]:
    return [
        PromptBlock(PromptBlockType.ROLE, " Principal architect ", order=8),
        PromptBlock(PromptBlockType.GOAL, " Design an offline system. ", order=2, enabled=False),
    ]


def test_prompt_editing_normalizes_and_persists_all_organization_fields(
    tmp_path: Path,
) -> None:
    database = tmp_path / DATABASE_FILE_NAME
    first = create_sqlite_container(database)
    project = first.project_service.create_project("Architecture")
    prompt = first.prompt_service.create_library_prompt(project.project_id, "Draft")
    original_updated_at = prompt.updated_at

    updated = first.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        " Architecture review ",
        " Engineering ",
        [" Offline ", "Design"],
        _blocks(),
    )
    second = create_sqlite_container(database)
    reopened = second.prompt_service.get_project_prompt(project.project_id, prompt.prompt_id)

    assert updated.updated_at >= original_updated_at
    assert reopened.title == "Architecture review"
    assert reopened.category == "Engineering"
    assert reopened.tags == {"Offline", "Design"}
    assert reopened.blocks == [
        PromptBlock(PromptBlockType.ROLE, "Principal architect", order=0),
        PromptBlock(PromptBlockType.GOAL, "Design an offline system.", order=1, enabled=False),
    ]
    assert CURRENT_SCHEMA_VERSION == 1


def test_project_scoped_search_matches_title_category_tag_and_block_content() -> None:
    container = create_in_memory_container()
    first = container.project_service.create_project("First")
    second = container.project_service.create_project("Second")
    first_prompt = container.prompt_service.create_library_prompt(first.project_id, "Release plan")
    container.prompt_service.update_library_prompt(
        first.project_id,
        first_prompt.prompt_id,
        "Release plan",
        "Delivery",
        ["Windows"],
        [PromptBlock(PromptBlockType.CONTEXT, "Installer readiness", order=0)],
    )
    container.prompt_service.create_library_prompt(second.project_id, "Windows elsewhere")

    assert container.prompt_service.search_project_prompts(first.project_id, "RELEASE") == [
        first_prompt
    ]
    assert container.prompt_service.search_project_prompts(first.project_id, "delivery") == [
        first_prompt
    ]
    assert container.prompt_service.search_project_prompts(first.project_id, "windows") == [
        first_prompt
    ]
    assert container.prompt_service.search_project_prompts(first.project_id, "installer") == [
        first_prompt
    ]
    assert container.prompt_service.search_project_prompts(first.project_id, "elsewhere") == []


def test_prompt_and_project_deletion_enforce_ownership_and_cascade(tmp_path: Path) -> None:
    container = create_sqlite_container(tmp_path / DATABASE_FILE_NAME)
    first = container.project_service.create_project("First")
    second = container.project_service.create_project("Second")
    first_prompt = container.prompt_service.create_library_prompt(first.project_id, "First prompt")
    container.prompt_service.create_library_prompt(first.project_id, "Dependent prompt")
    second_prompt = container.prompt_service.create_library_prompt(second.project_id, "Keep me")

    with pytest.raises(LookupError):
        container.prompt_service.delete_library_prompt(second.project_id, first_prompt.prompt_id)
    container.prompt_service.delete_library_prompt(first.project_id, first_prompt.prompt_id)
    deleted_count = container.project_service.delete_project(first.project_id)

    assert deleted_count == 1
    assert container.project_repository.get(first.project_id) is None
    assert container.prompt_repository.get(first_prompt.prompt_id) is None
    assert container.prompt_repository.get(second_prompt.prompt_id) == second_prompt


@pytest.mark.parametrize(
    ("category", "tags", "blocks"),
    [
        ("x" * 81, [], []),
        (None, ["duplicate", "DUPLICATE"], []),
        (None, ["line\nbreak"], []),
        (None, [], [PromptBlock(PromptBlockType.ROLE, " ", order=0)]),
        (
            None,
            [],
            [PromptBlock(PromptBlockType.ROLE, "valid", order=index) for index in range(13)],
        ),
    ],
)
def test_prompt_update_rejects_invalid_organization_and_blocks(
    category: str | None,
    tags: list[str],
    blocks: list[PromptBlock],
) -> None:
    container = create_in_memory_container()
    project = container.project_service.create_project("Validation")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Prompt")

    with pytest.raises(ValueError):
        container.prompt_service.update_library_prompt(
            project.project_id,
            prompt.prompt_id,
            "Prompt",
            category,
            tags,
            blocks,
        )


def test_missing_items_fail_without_cross_project_mutation() -> None:
    container = create_in_memory_container()
    project = container.project_service.create_project("Existing")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Existing")
    missing = "550e8400-e29b-41d4-a716-446655440000"

    with pytest.raises(LookupError):
        container.prompt_service.get_project_prompt(project.project_id, missing)
    with pytest.raises(LookupError):
        container.project_service.delete_project(missing)

    assert container.prompt_repository.get(prompt.prompt_id) == prompt
