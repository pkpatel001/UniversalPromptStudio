from Backend.application.prompt_builder import PromptBuilder
from Backend.domain.models import Prompt, PromptBlock, PromptBlockType


def test_prompt_builder_renders_enabled_blocks_in_order() -> None:
    prompt = Prompt(
        title="Architecture prompt",
        blocks=[
            PromptBlock(PromptBlockType.GOAL, "Design the app", order=2),
            PromptBlock(PromptBlockType.ROLE, "Senior architect", order=1),
            PromptBlock(PromptBlockType.CONTEXT, "Hidden", order=3, enabled=False),
        ],
    )

    rendered = PromptBuilder().build(prompt)

    assert rendered == "Role:\nSenior architect\n\nGoal:\nDesign the app"

