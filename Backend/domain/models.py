"""Core domain entities and value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class PromptBlockType(StrEnum):
    """Supported prompt builder block types."""

    ROLE = "role"
    GOAL = "goal"
    CONTEXT = "context"
    AUDIENCE = "audience"
    CONSTRAINTS = "constraints"
    REQUIREMENTS = "requirements"
    TONE = "tone"
    OUTPUT_FORMAT = "output_format"
    REASONING_STYLE = "reasoning_style"
    EXAMPLES = "examples"
    VALIDATION_RULES = "validation_rules"
    FINAL_INSTRUCTIONS = "final_instructions"


@dataclass(frozen=True)
class PromptBlock:
    """An editable building block used to assemble a prompt."""

    block_type: PromptBlockType
    content: str
    order: int
    enabled: bool = True


@dataclass
class Prompt:
    """A saved prompt definition."""

    title: str
    blocks: list[PromptBlock] = field(default_factory=list)
    prompt_id: str = field(default_factory=lambda: str(uuid4()))
    tags: set[str] = field(default_factory=set)
    category: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Project:
    """A prompt engineering workspace."""

    name: str
    project_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PromptExecutionRequest:
    """Input passed to a prompt executor or AI provider."""

    prompt: str
    provider_name: str
    parameters: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptExecutionResult:
    """Result returned after executing a prompt."""

    output: str
    provider_name: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

