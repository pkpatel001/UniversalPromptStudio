"""Whoosh-backed prompt search provider."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whoosh.fields import ID, KEYWORD, STORED, TEXT, Schema
from whoosh.index import create_in, exists_in, open_dir
from whoosh.qparser import MultifieldParser

from Backend.domain.models import Prompt, PromptBlock, PromptBlockType
from Backend.interfaces.providers import SearchProvider


class WhooshSearchProvider(SearchProvider):
    """Search provider that indexes prompt content with Whoosh."""

    def __init__(self, index_directory: Path) -> None:
        self._index_directory = index_directory
        self._index_directory.mkdir(parents=True, exist_ok=True)
        self._schema = Schema(
            prompt_id=ID(stored=True, unique=True),
            title=TEXT(stored=True),
            category=ID(stored=True),
            tags=KEYWORD(stored=True, commas=True, lowercase=True),
            content=TEXT,
            payload=STORED,
        )
        self._index = (
            open_dir(self._index_directory)
            if exists_in(self._index_directory)
            else create_in(self._index_directory, self._schema)
        )

    def index_prompt(self, prompt: Prompt) -> None:
        """Index or update a prompt."""

        writer = self._index.writer()
        writer.update_document(
            prompt_id=prompt.prompt_id,
            title=prompt.title,
            category=prompt.category or "",
            tags=",".join(sorted(prompt.tags)),
            content=_prompt_content(prompt),
            payload=json.dumps(_prompt_to_payload(prompt)),
        )
        writer.commit()

    def search(self, query: str) -> list[Prompt]:
        """Search prompts by title, category, tags, and block content."""

        if not query.strip():
            return []

        with self._index.searcher() as searcher:
            parser = MultifieldParser(["title", "category", "tags", "content"], schema=self._schema)
            results = searcher.search(parser.parse(query), limit=None)
            return [_prompt_from_payload(json.loads(str(result["payload"]))) for result in results]


def _prompt_content(prompt: Prompt) -> str:
    """Return searchable prompt text."""

    blocks = " ".join(block.content for block in prompt.blocks if block.enabled)
    tags = " ".join(sorted(prompt.tags))
    return f"{prompt.title} {prompt.category or ''} {tags} {blocks}"


def _prompt_to_payload(prompt: Prompt) -> dict[str, Any]:
    """Serialize a prompt into a JSON-compatible payload."""

    return {
        "prompt_id": prompt.prompt_id,
        "title": prompt.title,
        "category": prompt.category,
        "tags": sorted(prompt.tags),
        "created_at": prompt.created_at.isoformat(),
        "updated_at": prompt.updated_at.isoformat(),
        "blocks": [
            {
                "block_type": block.block_type.value,
                "content": block.content,
                "order": block.order,
                "enabled": block.enabled,
            }
            for block in prompt.blocks
        ],
    }


def _prompt_from_payload(payload: dict[str, Any]) -> Prompt:
    """Deserialize a prompt payload."""

    return Prompt(
        prompt_id=str(payload["prompt_id"]),
        title=str(payload["title"]),
        category=payload["category"] if payload["category"] is not None else None,
        tags={str(tag) for tag in payload["tags"]},
        created_at=_parse_datetime(str(payload["created_at"])),
        updated_at=_parse_datetime(str(payload["updated_at"])),
        blocks=[
            PromptBlock(
                block_type=PromptBlockType(str(block["block_type"])),
                content=str(block["content"]),
                order=int(block["order"]),
                enabled=bool(block["enabled"]),
            )
            for block in payload["blocks"]
        ],
    )


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO datetime and normalize it to UTC."""

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
