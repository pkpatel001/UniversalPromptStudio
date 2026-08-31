"""A-002.1 typed prompt-library IPC and restart tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from Backend.core.container import DESKTOP_APP_DATA_ENV, create_in_memory_container
from Backend.infrastructure.repositories.sqlite import DATABASE_FILE_NAME, FutureSchemaError
from Backend.ipc import (
    APPLICATION_READINESS_COMMAND,
    IPC_PROTOCOL_VERSION,
    PROJECT_CREATE_COMMAND,
    PROJECT_LIST_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_LIST_COMMAND,
    ApplicationIpcRouter,
    IpcErrorCode,
    parse_request,
)

ROOT = Path(__file__).resolve().parents[1]


def _request(command: str, payload: dict[str, object], request_id: str = "request-1") -> bytes:
    return json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": request_id,
            "command": command,
            "payload": payload,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _handle(
    router: ApplicationIpcRouter,
    command: str,
    payload: dict[str, object],
    request_id: str = "request-1",
) -> dict[str, object]:
    response = router.handle(parse_request(_request(command, payload, request_id)))
    return response.to_dict()  # type: ignore[return-value]


def test_router_creates_and_lists_project_scoped_prompts() -> None:
    router = ApplicationIpcRouter(create_in_memory_container)
    created_project = _handle(
        router,
        PROJECT_CREATE_COMMAND,
        {"name": " Product ", "description": " Offline library "},
        "project-create",
    )
    project = created_project["result"]["project"]  # type: ignore[index]
    project_id = project["project_id"]  # type: ignore[index]

    created_prompt = _handle(
        router,
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": " First prompt "},
        "prompt-create",
    )
    projects = _handle(router, PROJECT_LIST_COMMAND, {}, "project-list")
    prompts = _handle(
        router,
        PROMPT_LIST_COMMAND,
        {"project_id": project_id},
        "prompt-list",
    )

    assert created_project["request_id"] == "project-create"
    assert project["name"] == "Product"  # type: ignore[index]
    assert created_prompt["result"]["prompt"]["title"] == "First prompt"  # type: ignore[index]
    assert projects["result"]["projects"] == [project]  # type: ignore[index]
    assert prompts["result"]["prompts"] == [created_prompt["result"]["prompt"]]  # type: ignore[index]


@pytest.mark.parametrize(
    ("command", "payload"),
    [
        (PROJECT_LIST_COMMAND, {"extra": True}),
        (PROJECT_CREATE_COMMAND, {"name": "", "description": ""}),
        (PROJECT_CREATE_COMMAND, {"name": "Only name"}),
        (PROMPT_LIST_COMMAND, {"project_id": "../database"}),
        (
            PROMPT_CREATE_COMMAND,
            {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Prompt",
                "extra": True,
            },
        ),
    ],
)
def test_router_rejects_non_exact_library_payloads(
    command: str,
    payload: dict[str, object],
) -> None:
    response = _handle(ApplicationIpcRouter(), command, payload)

    assert response["ok"] is False
    assert response["error"]["code"] == IpcErrorCode.INVALID_PAYLOAD  # type: ignore[index]


def test_router_reports_missing_project_without_creating_prompt() -> None:
    router = ApplicationIpcRouter()
    response = _handle(
        router,
        PROMPT_CREATE_COMMAND,
        {
            "project_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Orphan",
        },
    )

    assert response["error"]["code"] == IpcErrorCode.NOT_FOUND  # type: ignore[index]


def test_router_exposes_safe_future_schema_recovery_state() -> None:
    def future_schema() -> None:
        raise FutureSchemaError("private path and detail")

    router = ApplicationIpcRouter(future_schema)  # type: ignore[arg-type]
    response = _handle(router, APPLICATION_READINESS_COMMAND, {})

    assert response["error"] == {  # type: ignore[index]
        "code": IpcErrorCode.FUTURE_SCHEMA.value,
        "message": "The prompt library was created by a newer application version.",
    }
    assert "private" not in json.dumps(response)


def _environment(app_data: Path) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ("SystemRoot", "TEMP", "TMP", "PATH", "APPDATA", "LOCALAPPDATA")
        if key in os.environ
    }
    environment["PYTHONPATH"] = str(ROOT)
    environment[DESKTOP_APP_DATA_ENV] = str(app_data)
    return environment


def _start_server(installed: Path, app_data: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-m", "Backend.ipc"],
        cwd=installed,
        env=_environment(app_data),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _exchange(
    process: subprocess.Popen[bytes],
    command: str,
    payload: dict[str, object],
    request_id: str,
) -> dict[str, object]:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(_request(command, payload, request_id) + b"\n")
    process.stdin.flush()
    response = process.stdout.readline()
    if not response:
        process.wait(timeout=5)
        assert process.stderr is not None
        detail = process.stderr.read().decode("utf-8", errors="replace")
        pytest.fail(f"IPC source subprocess exited without a response: {detail}")
    decoded = json.loads(response)
    assert isinstance(decoded, dict)
    return decoded


def _stop(process: subprocess.Popen[bytes]) -> None:
    assert process.stdin is not None
    process.stdin.close()
    assert process.wait(timeout=5) == 0
    assert process.stderr is not None
    assert process.stderr.read() == b""


def test_stdio_restart_uses_app_data_and_preserves_saved_records(tmp_path: Path) -> None:
    installed = tmp_path / "installed"
    app_data = tmp_path / "user-data"
    installed.mkdir()
    first = _start_server(installed, app_data)
    project_response = _exchange(
        first,
        PROJECT_CREATE_COMMAND,
        {"name": "Restart proof", "description": ""},
        "create-project",
    )
    project_id = project_response["result"]["project"]["project_id"]  # type: ignore[index]
    _exchange(
        first,
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Durable prompt"},
        "create-prompt",
    )
    _stop(first)

    second = _start_server(installed, app_data)
    projects = _exchange(second, PROJECT_LIST_COMMAND, {}, "list-projects")
    prompts = _exchange(
        second,
        PROMPT_LIST_COMMAND,
        {"project_id": project_id},
        "list-prompts",
    )
    _stop(second)

    assert projects["result"]["projects"][0]["name"] == "Restart proof"  # type: ignore[index]
    assert prompts["result"]["prompts"][0]["title"] == "Durable prompt"  # type: ignore[index]
    assert (app_data / DATABASE_FILE_NAME).is_file()
    assert list(installed.rglob("*.sqlite3")) == []
