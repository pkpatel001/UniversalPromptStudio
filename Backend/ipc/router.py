"""Closed application-owned command router for the desktop sidecar."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from Backend.application.services import (
    MAX_BLOCK_CONTENT_LENGTH,
    MAX_BLOCKS,
    MAX_CATEGORY_LENGTH,
    MAX_SEARCH_QUERY_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAGS,
)
from Backend.core.container import ApplicationContainer, create_in_memory_container
from Backend.domain.models import Project, Prompt, PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import (
    CURRENT_SCHEMA_VERSION,
    DatabaseUnavailableError,
    FutureSchemaError,
    InvalidDatabaseError,
)
from Engineering.core.version import VERSION

from .models import IPC_PROTOCOL_VERSION, IpcErrorCode, IpcRequest, IpcResponse, JsonValue

APPLICATION_READINESS_COMMAND = "application.readiness"
PROJECT_LIST_COMMAND = "library.projects.list"
PROJECT_CREATE_COMMAND = "library.projects.create"
PROJECT_DELETE_COMMAND = "library.projects.delete"
PROMPT_LIST_COMMAND = "library.prompts.list"
PROMPT_CREATE_COMMAND = "library.prompts.create"
PROMPT_GET_COMMAND = "library.prompts.get"
PROMPT_UPDATE_COMMAND = "library.prompts.update"
PROMPT_DELETE_COMMAND = "library.prompts.delete"
PROMPT_SEARCH_COMMAND = "library.prompts.search"
SIDECAR_IDENTITY = "com.universalpromptstudio.backend"
SUPPORTED_COMMANDS = (
    APPLICATION_READINESS_COMMAND,
    PROJECT_LIST_COMMAND,
    PROJECT_CREATE_COMMAND,
    PROJECT_DELETE_COMMAND,
    PROMPT_LIST_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_GET_COMMAND,
    PROMPT_UPDATE_COMMAND,
    PROMPT_DELETE_COMMAND,
    PROMPT_SEARCH_COMMAND,
)
MAX_LIBRARY_ITEMS = 50


class ApplicationIpcRouter:
    """Route validated requests through one long-lived application container."""

    def __init__(
        self,
        container_factory: Callable[[], ApplicationContainer] = create_in_memory_container,
    ) -> None:
        self._container: ApplicationContainer | None = None
        self._startup_error: tuple[IpcErrorCode, str] | None = None
        try:
            self._container = container_factory()
        except FutureSchemaError:
            self._startup_error = (
                IpcErrorCode.FUTURE_SCHEMA,
                "The prompt library was created by a newer application version.",
            )
        except InvalidDatabaseError:
            self._startup_error = (
                IpcErrorCode.INVALID_DATABASE,
                "The prompt library database is invalid and was left unchanged.",
            )
        except DatabaseUnavailableError:
            self._startup_error = (
                IpcErrorCode.STORAGE_UNAVAILABLE,
                "The prompt library database is unavailable.",
            )
        except Exception:
            self._startup_error = (
                IpcErrorCode.INTERNAL_ERROR,
                "The local application backend could not start safely.",
            )

    def handle(self, request: IpcRequest) -> IpcResponse:
        if request.command not in SUPPORTED_COMMANDS:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.UNKNOWN_COMMAND,
                "IPC command is not supported.",
            )
        if self._startup_error is not None:
            code, message = self._startup_error
            return IpcResponse.failure(request.request_id, code, message)
        if self._container is None:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.INTERNAL_ERROR,
                "The local application backend could not start safely.",
            )
        handlers = {
            APPLICATION_READINESS_COMMAND: self._readiness,
            PROJECT_LIST_COMMAND: self._list_projects,
            PROJECT_CREATE_COMMAND: self._create_project,
            PROJECT_DELETE_COMMAND: self._delete_project,
            PROMPT_LIST_COMMAND: self._list_prompts,
            PROMPT_CREATE_COMMAND: self._create_prompt,
            PROMPT_GET_COMMAND: self._get_prompt,
            PROMPT_UPDATE_COMMAND: self._update_prompt,
            PROMPT_DELETE_COMMAND: self._delete_prompt,
            PROMPT_SEARCH_COMMAND: self._search_prompts,
        }
        try:
            return handlers[request.command](request)
        except ValueError:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.INVALID_PAYLOAD,
                "IPC payload is invalid.",
            )
        except LookupError:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.NOT_FOUND,
                "The requested library item does not exist.",
            )
        except SQLAlchemyError:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.STORAGE_UNAVAILABLE,
                "The prompt library database is unavailable.",
            )
        except Exception:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.INTERNAL_ERROR,
                "IPC request failed safely.",
            )

    def _readiness(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset())
        result: dict[str, JsonValue] = {
            "status": "ready",
            "sidecar_identity": SIDECAR_IDENTITY,
            "application_version": VERSION,
            "protocol_version": IPC_PROTOCOL_VERSION,
            "storage_schema_version": CURRENT_SCHEMA_VERSION,
            "capabilities": list(SUPPORTED_COMMANDS),
        }
        return IpcResponse.success(request.request_id, result)

    def _list_projects(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset())
        assert self._container is not None
        projects = self._container.project_service.list_projects()
        return IpcResponse.success(
            request.request_id,
            _bounded_collection("projects", [_project_value(project) for project in projects]),
        )

    def _create_project(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"name", "description"}))
        name = _bounded_string(request.payload["name"], 120)
        description = _bounded_string(request.payload["description"], 1_000, allow_empty=True)
        assert self._container is not None
        project = self._container.project_service.create_project(name, description)
        return IpcResponse.success(request.request_id, {"project": _project_value(project)})

    def _delete_project(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"project_id", "confirm"}))
        project_id = _canonical_identifier(request.payload["project_id"])
        _require_confirmation(request.payload["confirm"])
        assert self._container is not None
        deleted_prompt_count = self._container.project_service.delete_project(project_id)
        return IpcResponse.success(
            request.request_id,
            {"deleted_project_id": project_id, "deleted_prompt_count": deleted_prompt_count},
        )

    def _list_prompts(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"project_id"}))
        project_id = _canonical_identifier(request.payload["project_id"])
        assert self._container is not None
        prompts = self._container.prompt_service.list_project_prompts(project_id)
        return IpcResponse.success(
            request.request_id,
            _bounded_collection("prompts", [_prompt_value(prompt) for prompt in prompts]),
        )

    def _create_prompt(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"project_id", "title"}))
        project_id = _canonical_identifier(request.payload["project_id"])
        title = _bounded_string(request.payload["title"], 120)
        assert self._container is not None
        prompt = self._container.prompt_service.create_library_prompt(project_id, title)
        return IpcResponse.success(request.request_id, {"prompt": _prompt_value(prompt)})

    def _get_prompt(self, request: IpcRequest) -> IpcResponse:
        project_id, prompt_id = _prompt_identifiers(request.payload)
        assert self._container is not None
        prompt = self._container.prompt_service.get_project_prompt(project_id, prompt_id)
        return IpcResponse.success(request.request_id, {"prompt": _prompt_value(prompt)})

    def _update_prompt(self, request: IpcRequest) -> IpcResponse:
        _require_fields(
            request.payload,
            frozenset({"project_id", "prompt_id", "title", "category", "tags", "blocks"}),
        )
        project_id = _canonical_identifier(request.payload["project_id"])
        prompt_id = _canonical_identifier(request.payload["prompt_id"])
        title = _bounded_string(request.payload["title"], 120)
        category = _optional_bounded_string(request.payload["category"], MAX_CATEGORY_LENGTH)
        tags = _tag_values(request.payload["tags"])
        blocks = _block_values(request.payload["blocks"])
        assert self._container is not None
        prompt = self._container.prompt_service.update_library_prompt(
            project_id,
            prompt_id,
            title,
            category,
            tags,
            blocks,
        )
        return IpcResponse.success(request.request_id, {"prompt": _prompt_value(prompt)})

    def _delete_prompt(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"project_id", "prompt_id", "confirm"}))
        project_id = _canonical_identifier(request.payload["project_id"])
        prompt_id = _canonical_identifier(request.payload["prompt_id"])
        _require_confirmation(request.payload["confirm"])
        assert self._container is not None
        self._container.prompt_service.delete_library_prompt(project_id, prompt_id)
        return IpcResponse.success(request.request_id, {"deleted_prompt_id": prompt_id})

    def _search_prompts(self, request: IpcRequest) -> IpcResponse:
        _require_fields(request.payload, frozenset({"project_id", "query"}))
        project_id = _canonical_identifier(request.payload["project_id"])
        query = _bounded_string(request.payload["query"], MAX_SEARCH_QUERY_LENGTH)
        assert self._container is not None
        prompts = self._container.prompt_service.search_project_prompts(project_id, query)
        return IpcResponse.success(
            request.request_id,
            _bounded_collection("prompts", [_prompt_value(prompt) for prompt in prompts]),
        )


def _require_fields(payload: dict[str, JsonValue], expected: frozenset[str]) -> None:
    if set(payload) != expected:
        raise ValueError("Payload fields do not match the command schema.")


def _bounded_string(value: JsonValue, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("Payload value must be text.")
    normalized = value.strip()
    if (not normalized and not allow_empty) or len(normalized) > maximum:
        raise ValueError("Payload text is outside its supported bounds.")
    return normalized


def _optional_bounded_string(value: JsonValue, maximum: int) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, maximum, allow_empty=True) or None


def _canonical_identifier(value: JsonValue) -> str:
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Identifier is invalid.")
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("Identifier is not canonical.")
    return value


def _prompt_identifiers(payload: dict[str, JsonValue]) -> tuple[str, str]:
    _require_fields(payload, frozenset({"project_id", "prompt_id"}))
    return (
        _canonical_identifier(payload["project_id"]),
        _canonical_identifier(payload["prompt_id"]),
    )


def _require_confirmation(value: JsonValue) -> None:
    if value is not True:
        raise ValueError("Deletion requires explicit confirmation.")


def _tag_values(value: JsonValue) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_TAGS:
        raise ValueError("Prompt tags are invalid.")
    tags = [_bounded_string(tag, MAX_TAG_LENGTH) for tag in value]
    if any("\n" in tag or "\r" in tag for tag in tags):
        raise ValueError("Prompt tags must be single-line text.")
    if len({tag.casefold() for tag in tags}) != len(tags):
        raise ValueError("Prompt tags must be unique ignoring case.")
    return tags


def _block_values(value: JsonValue) -> list[PromptBlock]:
    if not isinstance(value, list) or len(value) > MAX_BLOCKS:
        raise ValueError("Prompt blocks are invalid.")
    blocks: list[PromptBlock] = []
    for order, raw_block in enumerate(value):
        if not isinstance(raw_block, dict):
            raise ValueError("Prompt block is invalid.")
        _require_fields(raw_block, frozenset({"block_type", "content", "enabled"}))
        block_type_value = raw_block["block_type"]
        enabled = raw_block["enabled"]
        if not isinstance(block_type_value, str) or not isinstance(enabled, bool):
            raise ValueError("Prompt block is invalid.")
        blocks.append(
            PromptBlock(
                block_type=PromptBlockType(block_type_value),
                content=_bounded_string(raw_block["content"], MAX_BLOCK_CONTENT_LENGTH),
                order=order,
                enabled=enabled,
            )
        )
    return blocks


def _bounded_collection(name: str, values: list[dict[str, JsonValue]]) -> dict[str, JsonValue]:
    selected: list[JsonValue] = list(values[:MAX_LIBRARY_ITEMS])
    return {
        name: selected,
        "has_more": len(values) > len(selected),
    }


def _project_value(project: Project) -> dict[str, JsonValue]:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "description": project.description,
        "created_at": _timestamp(project.created_at),
    }


def _prompt_value(prompt: Prompt) -> dict[str, JsonValue]:
    if prompt.project_id is None:
        raise ValueError("Library prompt has no project ownership.")
    blocks: list[JsonValue] = [
        {
            "block_type": block.block_type.value,
            "content": block.content,
            "order": order,
            "enabled": block.enabled,
        }
        for order, block in enumerate(sorted(prompt.blocks, key=lambda item: item.order))
    ]
    sorted_tags = sorted(prompt.tags, key=str.casefold)
    tags: list[JsonValue] = list(sorted_tags)
    return {
        "prompt_id": prompt.prompt_id,
        "project_id": prompt.project_id,
        "title": prompt.title,
        "category": prompt.category,
        "tags": tags,
        "blocks": blocks,
        "created_at": _timestamp(prompt.created_at),
        "updated_at": _timestamp(prompt.updated_at),
    }


def _timestamp(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")
