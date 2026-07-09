"""Simple implementations used during phase-one development."""

from __future__ import annotations

from collections.abc import Sequence

from Backend.domain.models import Prompt, PromptExecutionRequest, PromptExecutionResult
from Backend.interfaces.providers import (
    AIProvider,
    EmbeddingProvider,
    ExportProvider,
    HistoryProvider,
    PromptOptimizer,
    PromptValidator,
    SearchProvider,
    SettingsProvider,
    TemplateProvider,
    WorkflowEngine,
)


class DummyAIProvider(AIProvider):
    """Offline provider that echoes the prompt for deterministic development."""

    @property
    def name(self) -> str:
        """Return the provider name."""

        return "dummy"

    def execute(self, request: PromptExecutionRequest) -> PromptExecutionResult:
        """Return a deterministic response without network access."""

        return PromptExecutionResult(
            output=f"[dummy response]\n{request.prompt}",
            provider_name=self.name,
            metadata={"offline": True},
        )


class BasicPromptValidator(PromptValidator):
    """Minimal validator that rejects empty prompts."""

    def validate(self, prompt: str) -> list[str]:
        """Return validation errors for a prompt."""

        if not prompt.strip():
            return ["Prompt cannot be empty."]
        return []


class NoOpPromptOptimizer(PromptOptimizer):
    """Optimizer that preserves prompt text."""

    def optimize(self, prompt: str) -> str:
        """Return the prompt unchanged."""

        return prompt


class FilesystemTemplateProvider(TemplateProvider):
    """Placeholder template provider for filesystem-backed templates."""

    def __init__(self, templates: list[str] | None = None) -> None:
        self._templates = templates or []

    def list_templates(self) -> list[str]:
        """Return configured template names."""

        return list(self._templates)


class BasicSearchProvider(SearchProvider):
    """In-memory search provider used until Whoosh is wired in."""

    def __init__(self) -> None:
        self._prompts: dict[str, Prompt] = {}

    def index_prompt(self, prompt: Prompt) -> None:
        """Index a prompt in memory."""

        self._prompts[prompt.prompt_id] = prompt

    def search(self, query: str) -> list[Prompt]:
        """Return prompts whose title or block content contains the query."""

        needle = query.lower()
        return [
            prompt
            for prompt in self._prompts.values()
            if needle in prompt.title.lower()
            or any(needle in block.content.lower() for block in prompt.blocks)
        ]


class SequentialWorkflowEngine(WorkflowEngine):
    """Sequential workflow engine for phase one."""

    def run(self, steps: Sequence[str]) -> list[str]:
        """Return steps in execution order."""

        return list(steps)


class MarkdownExportProvider(ExportProvider):
    """Export prompts as Markdown."""

    def export(self, prompt: Prompt) -> bytes:
        """Serialize a prompt to Markdown bytes."""

        blocks = "\n\n".join(
            f"## {block.block_type.value.replace('_', ' ').title()}\n{block.content}"
            for block in sorted(prompt.blocks, key=lambda item: item.order)
            if block.enabled
        )
        return f"# {prompt.title}\n\n{blocks}\n".encode("utf-8")


class InMemoryEmbeddingProvider(EmbeddingProvider):
    """Deterministic placeholder embedding provider."""

    def embed(self, text: str) -> list[float]:
        """Return a tiny deterministic embedding."""

        return [float(len(text)), float(sum(ord(char) for char in text) % 997)]


class InMemoryHistoryProvider(HistoryProvider):
    """In-memory execution history."""

    def __init__(self) -> None:
        self.entries: list[tuple[PromptExecutionRequest, PromptExecutionResult]] = []

    def record(self, request: PromptExecutionRequest, result: PromptExecutionResult) -> None:
        """Record a request and result pair."""

        self.entries.append((request, result))


class InMemorySettingsProvider(SettingsProvider):
    """In-memory settings provider."""

    def __init__(self) -> None:
        self._settings: dict[str, str] = {}

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return a setting value."""

        return self._settings.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Persist a setting value."""

        self._settings[key] = value
