"""Real frozen-sidecar lifecycle acceptance tests through A-002.1."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from Backend.core.container import DESKTOP_APP_DATA_ENV
from Backend.infrastructure.repositories.sqlite import DATABASE_FILE_NAME
from Backend.ipc import (
    IPC_PROTOCOL_VERSION,
    PROJECT_CREATE_COMMAND,
    PROJECT_LIST_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_LIST_COMMAND,
    SIDECAR_IDENTITY,
)
from Engineering.core.version import VERSION

ROOT = Path(__file__).resolve().parents[1]
SIDECAR_BASENAME = "universal-prompt-studio-backend"
CAPABILITIES = [
    "application.readiness",
    "library.projects.list",
    "library.projects.create",
    "library.prompts.list",
    "library.prompts.create",
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
    _command(
        first,
        "create-prompt",
        PROMPT_CREATE_COMMAND,
        {"project_id": project_id, "title": "Installed prompt"},
    )
    _stop(first)

    second = _start(installed, app_data)
    projects = _command(second, "list-projects", PROJECT_LIST_COMMAND, {})
    prompts = _command(
        second,
        "list-prompts",
        PROMPT_LIST_COMMAND,
        {"project_id": project_id},
    )
    _stop(second)

    assert projects["result"]["projects"][0]["name"] == "Installed project"  # type: ignore[index]
    assert prompts["result"]["prompts"][0]["title"] == "Installed prompt"  # type: ignore[index]
    assert (app_data / DATABASE_FILE_NAME).is_file()
    assert list(installed.parent.rglob("*.sqlite3")) == []
