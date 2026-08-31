"""A-002.2 typed prompt-management IPC tests."""

from __future__ import annotations

import json

import pytest

from Backend.core.container import create_in_memory_container
from Backend.ipc import (
    IPC_PROTOCOL_VERSION,
    PROJECT_CREATE_COMMAND,
    PROJECT_DELETE_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_DELETE_COMMAND,
    PROMPT_GET_COMMAND,
    PROMPT_SEARCH_COMMAND,
    PROMPT_UPDATE_COMMAND,
    ApplicationIpcRouter,
    IpcErrorCode,
    parse_request,
)


def _handle(
    router: ApplicationIpcRouter,
    command: str,
    payload: dict[str, object],
) -> dict[str, object]:
    request = json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": "management-request",
            "command": command,
            "payload": payload,
        },
        separators=(",", ":"),
    ).encode()
    return router.handle(parse_request(request)).to_dict()  # type: ignore[return-value]


def _create_project_and_prompt(router: ApplicationIpcRouter) -> tuple[str, str]:
    project_response = _handle(
        router,
        PROJECT_CREATE_COMMAND,
        {"name": "Library", "description": ""},
    )
    project_id = project_response["result"]["project"]["project_id"]  # type: ignore[index]
    prompt_response = _handle(
        router,
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Draft"},
    )
    prompt_id = prompt_response["result"]["prompt"]["prompt_id"]  # type: ignore[index]
    return project_id, prompt_id


def test_router_updates_gets_and_searches_full_prompt_details() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    project_id, prompt_id = _create_project_and_prompt(router)

    updated = _handle(
        router,
        PROMPT_UPDATE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "title": "Release prompt",
            "category": "Delivery",
            "tags": ["Windows", "Offline"],
            "blocks": [
                {"block_type": "role", "content": "Release lead", "enabled": True},
                {"block_type": "goal", "content": "Ship installer", "enabled": False},
            ],
        },
    )
    fetched = _handle(
        router,
        PROMPT_GET_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id},
    )
    searched = _handle(
        router,
        PROMPT_SEARCH_COMMAND,
        {"project_id": project_id, "query": "INSTALLER"},
    )

    prompt = updated["result"]["prompt"]  # type: ignore[index]
    assert prompt["category"] == "Delivery"  # type: ignore[index]
    assert prompt["tags"] == ["Offline", "Windows"]  # type: ignore[index]
    assert prompt["blocks"][0] == {  # type: ignore[index]
        "block_type": "role",
        "content": "Release lead",
        "order": 0,
        "enabled": True,
    }
    assert fetched["result"]["prompt"] == prompt  # type: ignore[index]
    assert searched["result"]["prompts"] == [prompt]  # type: ignore[index]


def test_router_deletes_prompt_and_project_only_with_confirmation() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    project_id, prompt_id = _create_project_and_prompt(router)

    rejected = _handle(
        router,
        PROMPT_DELETE_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id, "confirm": False},
    )
    deleted_prompt = _handle(
        router,
        PROMPT_DELETE_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id, "confirm": True},
    )
    deleted_project = _handle(
        router,
        PROJECT_DELETE_COMMAND,
        {"project_id": project_id, "confirm": True},
    )

    assert rejected["error"]["code"] == IpcErrorCode.INVALID_PAYLOAD  # type: ignore[index]
    assert deleted_prompt["result"] == {"deleted_prompt_id": prompt_id}
    assert deleted_project["result"] == {
        "deleted_project_id": project_id,
        "deleted_prompt_count": 0,
    }


@pytest.mark.parametrize(
    ("command", "payload"),
    [
        (PROJECT_DELETE_COMMAND, {"project_id": "not-an-id", "confirm": True}),
        (
            PROMPT_GET_COMMAND,
            {"project_id": "550e8400-e29b-41d4-a716-446655440000"},
        ),
        (
            PROMPT_UPDATE_COMMAND,
            {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "prompt_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Prompt",
                "category": None,
                "tags": ["same", "SAME"],
                "blocks": [],
            },
        ),
        (
            PROMPT_DELETE_COMMAND,
            {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "prompt_id": "550e8400-e29b-41d4-a716-446655440001",
                "confirm": "yes",
            },
        ),
        (
            PROMPT_SEARCH_COMMAND,
            {"project_id": "550e8400-e29b-41d4-a716-446655440000", "query": " "},
        ),
    ],
)
def test_router_rejects_invalid_management_payloads(
    command: str,
    payload: dict[str, object],
) -> None:
    response = _handle(ApplicationIpcRouter(), command, payload)

    assert response["error"]["code"] == IpcErrorCode.INVALID_PAYLOAD  # type: ignore[index]


def test_router_rejects_cross_project_prompt_access() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    _first_project_id, prompt_id = _create_project_and_prompt(router)
    second_response = _handle(
        router,
        PROJECT_CREATE_COMMAND,
        {"name": "Second", "description": ""},
    )
    second_project_id = second_response["result"]["project"]["project_id"]  # type: ignore[index]

    response = _handle(
        router,
        PROMPT_GET_COMMAND,
        {"project_id": second_project_id, "prompt_id": prompt_id},
    )

    assert response["error"]["code"] == IpcErrorCode.NOT_FOUND  # type: ignore[index]
