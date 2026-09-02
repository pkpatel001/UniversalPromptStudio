"""A-001.1 strict application IPC protocol and readiness tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from Backend.core.container import (
    DESKTOP_APP_DATA_ENV,
    ApplicationContainer,
    create_in_memory_container,
)
from Backend.ipc import (
    APPLICATION_READINESS_COMMAND,
    IPC_PROTOCOL_VERSION,
    MAX_IPC_MESSAGE_BYTES,
    SIDECAR_IDENTITY,
    ApplicationIpcRouter,
    IpcErrorCode,
    IpcProtocolError,
    IpcServer,
    encode_response,
    parse_request,
)


def _request(
    *,
    request_id: str = "request-1",
    command: str = APPLICATION_READINESS_COMMAND,
    payload: dict[str, object] | None = None,
    schema_version: int = IPC_PROTOCOL_VERSION,
) -> bytes:
    return json.dumps(
        {
            "schema_version": schema_version,
            "request_id": request_id,
            "command": command,
            "payload": payload or {},
        }
    ).encode("utf-8")


def test_readiness_uses_one_long_lived_application_container() -> None:
    calls = 0

    def factory() -> ApplicationContainer:
        nonlocal calls
        calls += 1
        return create_in_memory_container()

    router = ApplicationIpcRouter(factory)
    first = router.handle(parse_request(_request(request_id="first")))
    second = router.handle(parse_request(_request(request_id="second")))

    assert calls == 1
    assert first.error is None and second.error is None
    assert first.result == {
        "status": "ready",
        "sidecar_identity": SIDECAR_IDENTITY,
        "application_version": "0.2.0-alpha",
        "protocol_version": 1,
        "storage_schema_version": 1,
        "capabilities": [
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
            "customizations.catalog",
            "themes.install",
            "themes.lifecycle",
            "extensions.activate",
            "extensions.deactivate",
            "workflows.operations.list",
            "workflows.list",
            "workflows.create",
            "workflows.get",
            "workflows.update",
            "workflows.delete",
            "workflows.plan",
            "workflows.execute",
        ],
    }
    assert second.request_id == "second"


@pytest.mark.parametrize(
    ("raw", "code", "request_id"),
    [
        (b"not-json", IpcErrorCode.INVALID_REQUEST, "invalid"),
        (b"[]", IpcErrorCode.INVALID_REQUEST, "invalid"),
        (
            b'{"schema_version":1,"request_id":"x","request_id":"y",'
            b'"command":"application.readiness","payload":{}}',
            IpcErrorCode.INVALID_REQUEST,
            "invalid",
        ),
        (
            b'{"schema_version":1,"request_id":"x","command":'
            b'"application.readiness","payload":{},"extra":true}',
            IpcErrorCode.INVALID_REQUEST,
            "x",
        ),
        (_request(schema_version=2), IpcErrorCode.UNSUPPORTED_PROTOCOL, "request-1"),
        (_request(request_id="bad id"), IpcErrorCode.INVALID_REQUEST, "invalid"),
        (_request(command="Python.import"), IpcErrorCode.INVALID_REQUEST, "request-1"),
        (
            b'{"schema_version":1,"request_id":"x","command":'
            b'"application.readiness","payload":NaN}',
            IpcErrorCode.INVALID_REQUEST,
            "invalid",
        ),
    ],
)
def test_protocol_rejects_invalid_envelopes(
    raw: bytes,
    code: IpcErrorCode,
    request_id: str,
) -> None:
    with pytest.raises(IpcProtocolError) as caught:
        parse_request(raw)
    assert caught.value.code is code
    assert caught.value.request_id == request_id


def test_router_rejects_unknown_command_and_payload() -> None:
    router = ApplicationIpcRouter()
    unknown = router.handle(parse_request(_request(command="application.unknown")))
    payload = router.handle(parse_request(_request(payload={"path": "Backend"})))

    assert unknown.error is not None
    assert unknown.error.code is IpcErrorCode.UNKNOWN_COMMAND
    assert payload.error is not None
    assert payload.error.code is IpcErrorCode.INVALID_PAYLOAD


def test_server_handles_multiple_correlated_lines_and_eof_without_writes(tmp_path: Path) -> None:
    before = tuple(tmp_path.rglob("*"))
    source = io.BytesIO(
        _request(request_id="one")
        + b"\n"
        + _request(request_id="two", command="application.unknown")
        + b"\n"
    )
    target = io.BytesIO()

    assert IpcServer().run(source, target) == 0

    responses = [json.loads(line) for line in target.getvalue().splitlines()]
    assert responses[0]["request_id"] == "one"
    assert responses[0]["ok"] is True
    assert responses[1]["request_id"] == "two"
    assert responses[1]["error"]["code"] == "ipc.unknown_command"
    assert tuple(tmp_path.rglob("*")) == before


def test_server_rejects_and_drains_oversized_line() -> None:
    source = io.BytesIO(b"x" * (MAX_IPC_MESSAGE_BYTES + 100) + b"\n" + _request() + b"\n")
    target = io.BytesIO()

    IpcServer().run(source, target)

    responses = [json.loads(line) for line in target.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == "ipc.message_too_large"
    assert responses[1]["ok"] is True


def test_response_encoding_is_deterministic_and_bounded() -> None:
    response = ApplicationIpcRouter().handle(parse_request(_request()))
    first = encode_response(response)
    second = encode_response(response)

    assert first == second
    assert len(first) <= MAX_IPC_MESSAGE_BYTES
    assert first.startswith(b'{"ok":true,"request_id":"request-1"')


def test_module_entrypoint_round_trips_one_request(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment[DESKTOP_APP_DATA_ENV] = str(tmp_path / "app-data")
    completed = subprocess.run(
        [sys.executable, "-m", "Backend.ipc"],
        input=_request(request_id="subprocess") + b"\n",
        capture_output=True,
        check=False,
        env=environment,
        timeout=5,
    )

    assert completed.returncode == 0
    assert completed.stderr == b""
    response = json.loads(completed.stdout)
    assert response["request_id"] == "subprocess"
    assert response["result"]["status"] == "ready"
