"""A-003 saved-prompt composition and offline execution acceptance tests."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from Backend.core.container import create_in_memory_container
from Backend.domain.models import PromptBlock, PromptBlockType
from Backend.ipc import (
    IPC_PROTOCOL_VERSION,
    PROJECT_CREATE_COMMAND,
    PROMPT_COMPOSE_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_EXECUTE_OFFLINE_COMMAND,
    PROMPT_UPDATE_COMMAND,
    ApplicationIpcRouter,
    IpcErrorCode,
    parse_request,
)

OFFLINE_PROVIDER = "ups.offline-echo"


def _saved_prompt() -> tuple[object, str, str]:
    container = create_in_memory_container()
    project = container.project_service.create_project("Runtime")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Release plan")
    container.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        prompt.title,
        "Delivery",
        ["Offline"],
        [
            PromptBlock(PromptBlockType.GOAL, "Ship the desktop build", 0),
            PromptBlock(PromptBlockType.CONTEXT, "Do not render this", 1, enabled=False),
            PromptBlock(PromptBlockType.OUTPUT_FORMAT, "Return a checklist", 2),
        ],
    )
    return container, project.project_id, prompt.prompt_id


def test_saved_prompt_runtime_composes_enabled_blocks_in_durable_order() -> None:
    container, project_id, prompt_id = _saved_prompt()

    composition = container.saved_prompt_runtime_service.compose(project_id, prompt_id)  # type: ignore[attr-defined]

    assert composition.project_id == project_id
    assert composition.prompt_id == prompt_id
    assert composition.title == "Release plan"
    assert composition.final_prompt == (
        "Goal:\nShip the desktop build\n\nOutput Format:\nReturn a checklist"
    )
    assert composition.enabled_block_count == 2
    assert composition.total_block_count == 3
    assert composition.character_count == len(composition.final_prompt)


def test_saved_prompt_runtime_recomposes_and_executes_only_offline_echo() -> None:
    container, project_id, prompt_id = _saved_prompt()

    composition, result = container.saved_prompt_runtime_service.execute_offline(  # type: ignore[attr-defined]
        project_id,
        prompt_id,
    )

    assert result.provider_name == OFFLINE_PROVIDER
    assert result.output == f"[offline provider response]\n{composition.final_prompt}"
    assert result.metadata["provider_id"] == OFFLINE_PROVIDER
    assert result.metadata["provider_version"] == "1.0.0"
    assert UUID(str(result.metadata["request_id"]))
    assert result.metadata["input_units"] == len(composition.final_prompt)
    assert result.metadata["output_units"] == len(composition.final_prompt)


def test_saved_prompt_runtime_rejects_empty_or_cross_project_composition() -> None:
    container = create_in_memory_container()
    first = container.project_service.create_project("First")
    second = container.project_service.create_project("Second")
    prompt = container.prompt_service.create_library_prompt(first.project_id, "Empty")

    with pytest.raises(ValueError, match="enabled block"):
        container.saved_prompt_runtime_service.compose(first.project_id, prompt.prompt_id)
    with pytest.raises(LookupError, match="does not exist"):
        container.saved_prompt_runtime_service.compose(second.project_id, prompt.prompt_id)


def _handle(
    router: ApplicationIpcRouter,
    command: str,
    payload: dict[str, object],
) -> dict[str, object]:
    request = json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": "runtime-request",
            "command": command,
            "payload": payload,
        },
        separators=(",", ":"),
    ).encode()
    return router.handle(parse_request(request)).to_dict()  # type: ignore[return-value]


def _create_routable_prompt(router: ApplicationIpcRouter) -> tuple[str, str]:
    project = _handle(
        router,
        PROJECT_CREATE_COMMAND,
        {"name": "Runtime", "description": ""},
    )
    project_id = project["result"]["project"]["project_id"]  # type: ignore[index]
    prompt = _handle(
        router,
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Offline prompt"},
    )
    prompt_id = prompt["result"]["prompt"]["prompt_id"]  # type: ignore[index]
    updated = _handle(
        router,
        PROMPT_UPDATE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "title": "Offline prompt",
            "category": None,
            "tags": [],
            "blocks": [
                {"block_type": "role", "content": "Safety reviewer", "enabled": True},
                {"block_type": "goal", "content": "Hidden", "enabled": False},
            ],
        },
    )
    assert updated["ok"] is True
    return project_id, prompt_id


def test_router_composes_and_executes_saved_prompt_with_typed_results() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    project_id, prompt_id = _create_routable_prompt(router)

    composed = _handle(
        router,
        PROMPT_COMPOSE_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id},
    )
    executed = _handle(
        router,
        PROMPT_EXECUTE_OFFLINE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "provider_id": OFFLINE_PROVIDER,
            "confirm": True,
        },
    )

    composition = composed["result"]["composition"]  # type: ignore[index]
    assert composition == {
        "project_id": project_id,
        "prompt_id": prompt_id,
        "title": "Offline prompt",
        "final_prompt": "Role:\nSafety reviewer",
        "enabled_block_count": 1,
        "total_block_count": 2,
        "character_count": 21,
    }
    execution = executed["result"]["execution"]  # type: ignore[index]
    assert execution["project_id"] == project_id  # type: ignore[index]
    assert execution["prompt_id"] == prompt_id  # type: ignore[index]
    assert execution["provider_id"] == OFFLINE_PROVIDER  # type: ignore[index]
    assert execution["provider_version"] == "1.0.0"  # type: ignore[index]
    assert execution["output"] == "[offline provider response]\nRole:\nSafety reviewer"  # type: ignore[index]
    assert execution["prompt_character_count"] == 21  # type: ignore[index]
    assert UUID(execution["execution_id"])  # type: ignore[arg-type,index]


@pytest.mark.parametrize("provider_id, confirm", [("dummy", True), (OFFLINE_PROVIDER, False)])
def test_router_rejects_unapproved_or_unconfirmed_execution(
    provider_id: str,
    confirm: bool,
) -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    project_id, prompt_id = _create_routable_prompt(router)

    response = _handle(
        router,
        PROMPT_EXECUTE_OFFLINE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "provider_id": provider_id,
            "confirm": confirm,
        },
    )

    assert response["error"]["code"] == IpcErrorCode.INVALID_PAYLOAD  # type: ignore[index]
