"""Block-based prompt builder."""

from __future__ import annotations

from Backend.domain.models import Prompt, PromptBlock


class PromptBuilder:
    """Build final prompt text from ordered prompt blocks."""

    def build(self, prompt: Prompt) -> str:
        """Render enabled prompt blocks into a final prompt."""

        sections = [
            self._render_block(block)
            for block in sorted(prompt.blocks, key=lambda item: item.order)
            if block.enabled and block.content.strip()
        ]
        return "\n\n".join(sections)

    def _render_block(self, block: PromptBlock) -> str:
        title = block.block_type.value.replace("_", " ").title()
        return f"{title}:\n{block.content.strip()}"

