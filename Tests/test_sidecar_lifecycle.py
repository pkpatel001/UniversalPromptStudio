"""Real frozen-sidecar lifecycle acceptance tests for A-001.2."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from Backend.ipc import IPC_PROTOCOL_VERSION, SIDECAR_IDENTITY
from Engineering.core.version import VERSION

ROOT = Path(__file__).resolve().parents[1]
SIDECAR_BASENAME = "universal-prompt-studio-backend"


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


def _minimal_environment() -> dict[str, str]:
    return {key: os.environ[key] for key in ("SystemRoot", "TEMP", "TMP") if key in os.environ}


@pytest.fixture(scope="module")
def sidecar() -> Path:
    path = _sidecar_path()
    if not path.is_file():
        if os.environ.get("UPS_REQUIRE_SIDECAR_TESTS") == "1":
            pytest.fail(f"Required sidecar is missing: {path}")
        pytest.skip("Build the sidecar to run installed lifecycle acceptance tests.")
    return path


def _start(path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_minimal_environment(),
    )


def _request(process: subprocess.Popen[bytes], request_id: str) -> dict[str, object]:
    assert process.stdin is not None
    assert process.stdout is not None
    value = json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": request_id,
            "command": "application.readiness",
            "payload": {},
        },
        separators=(",", ":"),
    ).encode("utf-8")
    process.stdin.write(value + b"\n")
    process.stdin.flush()
    response = process.stdout.readline()
    assert response
    decoded = json.loads(response)
    assert isinstance(decoded, dict)
    return decoded


def _assert_readiness(response: dict[str, object], request_id: str) -> None:
    assert response["request_id"] == request_id
    assert response["ok"] is True
    assert response["result"] == {
        "status": "ready",
        "sidecar_identity": SIDECAR_IDENTITY,
        "application_version": VERSION,
        "protocol_version": IPC_PROTOCOL_VERSION,
        "capabilities": ["application.readiness"],
    }


def test_frozen_sidecar_starts_reuses_and_stops_on_eof(sidecar: Path) -> None:
    process = _start(sidecar)
    try:
        process_id = process.pid
        _assert_readiness(_request(process, "installed-one"), "installed-one")
        _assert_readiness(_request(process, "installed-two"), "installed-two")
        assert process.pid == process_id
        assert process.stdin is not None
        process.stdin.close()
        assert process.wait(timeout=3) == 0
        assert process.stderr is not None
        assert process.stderr.read() == b""
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)


def test_frozen_sidecar_recovers_after_crash(sidecar: Path) -> None:
    first = _start(sidecar)
    first_id = first.pid
    _assert_readiness(_request(first, "before-crash"), "before-crash")
    first.kill()
    first.wait(timeout=3)

    second = _start(sidecar)
    try:
        _assert_readiness(_request(second, "after-crash"), "after-crash")
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
