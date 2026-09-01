"""Real frozen-sidecar lifecycle acceptance tests through A-005."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from Backend.core.container import DESKTOP_APP_DATA_ENV
from Backend.infrastructure.repositories.sqlite import DATABASE_FILE_NAME
from Backend.infrastructure.workflow_definitions import WORKFLOW_DEFINITIONS_FILE_NAME
from Backend.ipc import (
    IPC_PROTOCOL_VERSION,
    PROJECT_CREATE_COMMAND,
    PROJECT_DELETE_COMMAND,
    PROJECT_LIST_COMMAND,
    PROMPT_COMPOSE_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_DELETE_COMMAND,
    PROMPT_EXECUTE_OFFLINE_COMMAND,
    PROMPT_GET_COMMAND,
    PROMPT_LIST_COMMAND,
    PROMPT_SEARCH_COMMAND,
    PROMPT_UPDATE_COMMAND,
    PROVIDER_CATALOG_COMMAND,
    PROVIDER_CREDENTIAL_CLEAR_COMMAND,
    PROVIDER_SETTINGS_SAVE_COMMAND,
    SIDECAR_IDENTITY,
    WORKFLOW_CREATE_COMMAND,
    WORKFLOW_EXECUTE_COMMAND,
    WORKFLOW_LIST_COMMAND,
    WORKFLOW_OPERATIONS_COMMAND,
    WORKFLOW_PLAN_COMMAND,
)
from Engineering.core.version import VERSION

ROOT = Path(__file__).resolve().parents[1]
SIDECAR_BASENAME = "universal-prompt-studio-backend"
CAPABILITIES = [
    "application.readiness",
    "library.projects.list",
    "library.projects.create",
    "library.projects.delete",
    "library.prompts.list",
    "library.prompts.create",
    "library.prompts.get",
    "library.prompts.update",
    "library.prompts.delete",
    "library.prompts.search",
    "library.prompts.compose",
    "library.prompts.execute-offline",
    "providers.catalog",
    "providers.settings.save",
    "providers.credentials.clear",
    "library.prompts.execute-configured",
    "workflows.operations.list",
    "workflows.list",
    "workflows.create",
    "workflows.get",
    "workflows.update",
    "workflows.delete",
    "workflows.plan",
    "workflows.execute",
]


def _sidecar_path() -> Path:
    completed = subprocess.run(
        ["rustc", "--print", "host-tuple"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    extension = ".exe" if os.name == "nt" else ""
    return (
        ROOT
        / "Frontend"
        / "src-tauri"
        / "binaries"
        / f"{SIDECAR_BASENAME}-{completed.stdout.strip()}{extension}"
    )


def _minimal_environment(app_data: Path | None = None) -> dict[str, str]:
    environment = {
        key: os.environ[key] for key in ("SystemRoot", "TEMP", "TMP") if key in os.environ
    }
    if app_data is not None:
        environment[DESKTOP_APP_DATA_ENV] = str(app_data)
    return environment


@pytest.fixture(scope="module")
def sidecar() -> Path:
    path = _sidecar_path()
    if not path.is_file():
        if os.environ.get("UPS_REQUIRE_SIDECAR_TESTS") == "1":
            pytest.fail(f"Required sidecar is missing: {path}")
        pytest.skip("Build the sidecar to run installed lifecycle acceptance tests.")
    return path


def _start(path: Path, app_data: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_minimal_environment(app_data),
    )


def _command(
    process: subprocess.Popen[bytes],
    request_id: str,
    command: str,
    payload: dict[str, object],
) -> dict[str, object]:
    assert process.stdin is not None
    assert process.stdout is not None
    value = json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": request_id,
            "command": command,
            "payload": payload,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    process.stdin.write(value + b"\n")
    process.stdin.flush()
    response = process.stdout.readline()
    if not response:
        process.wait(timeout=5)
        assert process.stderr is not None
        detail = process.stderr.read().decode("utf-8", errors="replace")
        pytest.fail(f"Frozen sidecar exited without a response: {detail}")
    decoded = json.loads(response)
    assert isinstance(decoded, dict)
    return decoded


def _readiness(process: subprocess.Popen[bytes], request_id: str) -> dict[str, object]:
    return _command(process, request_id, "application.readiness", {})


def _echo_workflow() -> dict[str, object]:
    input_port = {
        "id": "value",
        "type": "string",
        "description": "Text supplied to the operation.",
    }
    output_port = {
        "id": "value",
        "type": "string",
        "description": "Text returned by the operation.",
    }
    return {
        "schema_version": 1,
        "workflow": {
            "id": "ups.installed-echo",
            "name": "Installed Echo",
            "version": "1.0.0",
            "sdk_version": 1,
            "description": "Installed lifecycle workflow.",
            "inputs": [
                {"id": "input", "type": "string", "description": "Workflow text."}
            ],
            "outputs": [
                {"id": "output", "type": "string", "description": "Workflow result."}
            ],
            "nodes": [
                {
                    "id": "echo",
                    "operation": "ups.echo-text",
                    "inputs": [input_port],
                    "outputs": [output_port],
                }
            ],
            "edges": [
                {
                    "source": {"workflow_input": "input"},
                    "target": {"node": "echo", "port": "value"},
                },
                {
                    "source": {"node": "echo", "port": "value"},
                    "target": {"workflow_output": "output"},
                },
            ],
        },
    }


def _assert_readiness(response: dict[str, object], request_id: str) -> None:
    assert response["request_id"] == request_id
    assert response["ok"] is True
    assert response["result"] == {
        "status": "ready",
        "sidecar_identity": SIDECAR_IDENTITY,
        "application_version": VERSION,
        "protocol_version": IPC_PROTOCOL_VERSION,
        "storage_schema_version": 1,
        "capabilities": CAPABILITIES,
    }


def _stop(process: subprocess.Popen[bytes]) -> None:
    assert process.stdin is not None
    process.stdin.close()
    assert process.wait(timeout=5) == 0
    assert process.stderr is not None
    assert process.stderr.read() == b""


def test_frozen_sidecar_starts_reuses_and_stops_on_eof(
    sidecar: Path,
    tmp_path: Path,
) -> None:
    process = _start(sidecar, tmp_path / "app-data")
    try:
        process_id = process.pid
        _assert_readiness(_readiness(process, "installed-one"), "installed-one")
        _assert_readiness(_readiness(process, "installed-two"), "installed-two")
        assert process.pid == process_id
        _stop(process)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)


def test_frozen_sidecar_recovers_after_crash(sidecar: Path, tmp_path: Path) -> None:
    app_data = tmp_path / "app-data"
    first = _start(sidecar, app_data)
    first_id = first.pid
    _assert_readiness(_readiness(first, "before-crash"), "before-crash")
    first.kill()
    first.wait(timeout=3)

    second = _start(sidecar, app_data)
    try:
        _assert_readiness(_readiness(second, "after-crash"), "after-crash")
        assert second.pid != first_id
    finally:
        second.kill()
        second.wait(timeout=3)


def test_installed_layout_preserves_identity_and_protocol(sidecar: Path, tmp_path: Path) -> None:
    installed = tmp_path / "Universal Prompt Studio" / f"{SIDECAR_BASENAME}.exe"
    installed.parent.mkdir(parents=True)
    shutil.copy2(sidecar, installed)
    completed = subprocess.run(
        [str(installed), "--identity"],
        capture_output=True,
        check=True,
        timeout=5,
        env=_minimal_environment(),
    )
    assert json.loads(completed.stdout) == {
        "application_version": VERSION,
        "protocol_version": IPC_PROTOCOL_VERSION,
        "sidecar_identity": SIDECAR_IDENTITY,
    }
    assert completed.stderr == b""


def test_installed_sidecar_persists_library_only_in_app_data(
    sidecar: Path,
    tmp_path: Path,
) -> None:
    installed = tmp_path / "installed" / f"{SIDECAR_BASENAME}.exe"
    installed.parent.mkdir()
    shutil.copy2(sidecar, installed)
    app_data = tmp_path / "per-user-app-data"
    first = _start(installed, app_data)
    project_response = _command(
        first,
        "create-project",
        PROJECT_CREATE_COMMAND,
        {"name": "Installed project", "description": ""},
    )
    project_id = project_response["result"]["project"]["project_id"]  # type: ignore[index]
    prompt_response = _command(
        first,
        "create-prompt",
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Installed prompt"},
    )
    prompt_id = prompt_response["result"]["prompt"]["prompt_id"]  # type: ignore[index]
    _command(
        first,
        "update-prompt",
        PROMPT_UPDATE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "title": "Installed release prompt",
            "category": "Delivery",
            "tags": ["Windows", "Offline"],
            "blocks": [
                {
                    "block_type": "goal",
                    "content": "Ship the installer",
                    "enabled": True,
                }
            ],
        },
    )
    secret = "sk-installed-a004-never-plaintext"
    saved_provider = _command(
        first,
        "save-provider",
        PROVIDER_SETTINGS_SAVE_COMMAND,
        {
            "provider_id": "ups.openai-responses",
            "endpoint": "https://api.openai.com/v1/responses",
            "model": "gpt-5-mini",
            "temperature": 1.0,
            "max_output_tokens": 512,
            "credential": secret,
        },
    )
    created_workflow = _command(
        first,
        "create-workflow",
        WORKFLOW_CREATE_COMMAND,
        {"workflow": _echo_workflow()},
    )
    _stop(first)
    second = _start(installed, app_data)
    credential_files = list((app_data / "credentials").glob("*.dpapi"))
    assert len(credential_files) == 1
    encrypted_credential = credential_files[0].read_bytes()
    projects = _command(second, "list-projects", PROJECT_LIST_COMMAND, {})
    prompts = _command(
        second,
        "list-prompts",
        PROMPT_LIST_COMMAND,
        {"project_id": project_id},
    )
    provider_catalog = _command(second, "provider-catalog", PROVIDER_CATALOG_COMMAND, {})
    workflow_operations = _command(
        second, "workflow-operations", WORKFLOW_OPERATIONS_COMMAND, {}
    )
    workflows = _command(second, "list-workflows", WORKFLOW_LIST_COMMAND, {})
    workflow_plan = _command(
        second,
        "plan-workflow",
        WORKFLOW_PLAN_COMMAND,
        {"workflow_id": "ups.installed-echo"},
    )
    workflow_execution = _command(
        second,
        "execute-workflow",
        WORKFLOW_EXECUTE_COMMAND,
        {
            "workflow_id": "ups.installed-echo",
            "run_id": "550e8400-e29b-41d4-a716-446655440000",
            "inputs": [{"port_id": "input", "value": "Installed"}],
            "confirm": True,
        },
    )
    cleared_provider = _command(
        second,
        "clear-provider",
        PROVIDER_CREDENTIAL_CLEAR_COMMAND,
        {"provider_id": "ups.openai-responses", "confirm": True},
    )
    fetched = _command(
        second,
        "get-prompt",
        PROMPT_GET_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id},
    )
    searched = _command(
        second,
        "search-prompts",
        PROMPT_SEARCH_COMMAND,
        {"project_id": project_id, "query": "INSTALLER"},
    )
    composed = _command(
        second,
        "compose-prompt",
        PROMPT_COMPOSE_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id},
    )
    executed = _command(
        second,
        "execute-prompt",
        PROMPT_EXECUTE_OFFLINE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "provider_id": "ups.offline-echo",
            "confirm": True,
        },
    )
    _command(
        second,
        "delete-prompt",
        PROMPT_DELETE_COMMAND,
        {"project_id": project_id, "prompt_id": prompt_id, "confirm": True},
    )
    replacement = _command(
        second,
        "create-dependent",
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Delete with project"},
    )
    deleted_project = _command(
        second,
        "delete-project",
        PROJECT_DELETE_COMMAND,
        {"project_id": project_id, "confirm": True},
    )
    remaining_projects = _command(second, "remaining-projects", PROJECT_LIST_COMMAND, {})
    _stop(second)

    assert projects["result"]["projects"][0]["name"] == "Installed project"  # type: ignore[index]
    persisted = prompts["result"]["prompts"][0]  # type: ignore[index]
    assert persisted["title"] == "Installed release prompt"  # type: ignore[index]
    assert persisted["category"] == "Delivery"  # type: ignore[index]
    assert persisted["tags"] == ["Offline", "Windows"]  # type: ignore[index]
    assert persisted["blocks"] == [  # type: ignore[index]
        {
            "block_type": "goal",
            "content": "Ship the installer",
            "order": 0,
            "enabled": True,
        }
    ]
    assert fetched["result"]["prompt"] == persisted  # type: ignore[index]
    assert searched["result"]["prompts"] == [persisted]  # type: ignore[index]
    composition = composed["result"]["composition"]  # type: ignore[index]
    assert composition["final_prompt"] == "Goal:\nShip the installer"  # type: ignore[index]
    assert composition["enabled_block_count"] == 1  # type: ignore[index]
    execution = executed["result"]["execution"]  # type: ignore[index]
    assert execution["provider_id"] == "ups.offline-echo"  # type: ignore[index]
    assert execution["provider_version"] == "1.0.0"  # type: ignore[index]
    assert execution["output"] == (  # type: ignore[index]
        "[offline provider response]\nGoal:\nShip the installer"
    )
    assert execution["prompt_character_count"] == len(  # type: ignore[index]
        composition["final_prompt"]  # type: ignore[index]
    )
    assert replacement["result"]["prompt"]["title"] == "Delete with project"  # type: ignore[index]
    assert deleted_project["result"] == {
        "deleted_project_id": project_id,
        "deleted_prompt_count": 1,
    }
    assert remaining_projects["result"] == {"projects": [], "has_more": False}
    assert saved_provider["result"]["provider"]["credential_state"] == "stored"  # type: ignore[index]
    remote = provider_catalog["result"]["providers"][1]  # type: ignore[index]
    assert remote["provider_id"] == "ups.openai-responses"  # type: ignore[index]
    assert remote["available"] is True  # type: ignore[index]
    assert remote["credential_state"] == "stored"  # type: ignore[index]
    assert created_workflow["result"]["workflow"] == _echo_workflow()  # type: ignore[index]
    operation_values = workflow_operations["result"]["operations"]  # type: ignore[index]
    assert [item["operation_id"] for item in operation_values] == [  # type: ignore[index]
        "ups.echo-text",
        "ups.execute-saved-prompt",
        "ups.uppercase-text",
    ]
    assert workflows["result"]["workflows"] == [  # type: ignore[index]
        {
            "workflow_id": "ups.installed-echo",
            "name": "Installed Echo",
            "version": "1.0.0",
            "description": "Installed lifecycle workflow.",
            "node_count": 1,
            "edge_count": 2,
        }
    ]
    assert workflow_plan["result"]["plan"]["valid"] is True  # type: ignore[index]
    assert workflow_execution["result"]["execution"]["outputs"] == [  # type: ignore[index]
        {"port_id": "output", "value": "Installed"}
    ]
    assert secret not in repr((saved_provider, provider_catalog, cleared_provider))
    assert secret.encode() not in encrypted_credential
    assert cleared_provider["result"]["provider"]["credential_state"] == "missing"  # type: ignore[index]
    assert secret.encode() not in (app_data / "provider-settings.json").read_bytes()
    assert list((app_data / "credentials").glob("*.dpapi")) == []
    assert (app_data / DATABASE_FILE_NAME).is_file()
    assert (app_data / WORKFLOW_DEFINITIONS_FILE_NAME).is_file()
    assert list(installed.parent.rglob("*.sqlite3")) == []
    assert list(installed.parent.rglob(WORKFLOW_DEFINITIONS_FILE_NAME)) == []
