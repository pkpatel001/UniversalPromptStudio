from pathlib import Path

from Backend.application.services import SearchService
from Backend.domain.models import Prompt, PromptBlock, PromptBlockType
from Backend.infrastructure.search.whoosh_search import WhooshSearchProvider


def test_whoosh_search_provider_finds_prompt_by_block_content(tmp_path: Path) -> None:
    provider = WhooshSearchProvider(tmp_path / "index")
    prompt = Prompt(
        title="Research Assistant",
        category="Research",
        tags={"literature"},
        blocks=[
            PromptBlock(PromptBlockType.ROLE, "Academic research partner", order=1),
            PromptBlock(PromptBlockType.GOAL, "Summarize robotics papers", order=2),
        ],
    )

    provider.index_prompt(prompt)
    results = provider.search("robotics")

    assert [result.prompt_id for result in results] == [prompt.prompt_id]
    assert results[0].blocks == prompt.blocks


def test_whoosh_search_provider_updates_existing_prompt(tmp_path: Path) -> None:
    provider = WhooshSearchProvider(tmp_path / "index")
    prompt = Prompt(title="Draft", blocks=[PromptBlock(PromptBlockType.GOAL, "First text", order=1)])
    provider.index_prompt(prompt)
    prompt.title = "Updated"
    prompt.blocks = [PromptBlock(PromptBlockType.GOAL, "Second text", order=1)]

    provider.index_prompt(prompt)

    assert provider.search("First") == []
    assert [result.title for result in provider.search("Second")] == ["Updated"]


def test_search_service_delegates_to_provider(tmp_path: Path) -> None:
    service = SearchService(WhooshSearchProvider(tmp_path / "index"))
    prompt = Prompt(title="Finance Template", tags={"finance"})

    service.index_prompt(prompt)

    assert [result.prompt_id for result in service.search("finance")] == [prompt.prompt_id]
