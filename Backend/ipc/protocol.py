"""Strict JSON-lines codec for the desktop application boundary."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, NoReturn

from .models import (
    IPC_PROTOCOL_VERSION,
    MAX_IPC_MESSAGE_BYTES,
    IpcErrorCode,
    IpcRequest,
    IpcResponse,
)

_REQUEST_KEYS = frozenset({"schema_version", "request_id", "command", "payload"})
_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
_COMMAND = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9-]*)+$")
INVALID_REQUEST_ID = "invalid"


class IpcProtocolError(ValueError):
    """A safe protocol failure that can be returned to the caller."""

    def __init__(self, code: IpcErrorCode, message: str, request_id: str = INVALID_REQUEST_ID):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.request_id = request_id

    def to_response(self) -> IpcResponse:
        return IpcResponse.failure(self.request_id, self.code, self.safe_message)


def _reject_constant(_value: str) -> NoReturn:
    raise ValueError("Non-finite JSON numbers are not supported.")


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _candidate_request_id(value: object) -> str:
    if isinstance(value, str) and _REQUEST_ID.fullmatch(value) is not None:
        return value
    return INVALID_REQUEST_ID


def parse_request(raw: bytes) -> IpcRequest:
    """Parse one bounded, exact request object."""

    if len(raw) > MAX_IPC_MESSAGE_BYTES:
        raise IpcProtocolError(
            IpcErrorCode.MESSAGE_TOO_LARGE,
            "IPC request exceeds the maximum message size.",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC request must be UTF-8 JSON.",
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC request must be one valid JSON object.",
        ) from exc
    if not isinstance(value, dict):
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC request must be a JSON object.",
        )
    request_id = _candidate_request_id(value.get("request_id"))
    if set(value) != _REQUEST_KEYS:
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC request fields do not match protocol schema 1.",
            request_id,
        )
    schema_version = value["schema_version"]
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC schema_version must be an integer.",
            request_id,
        )
    if schema_version != IPC_PROTOCOL_VERSION:
        raise IpcProtocolError(
            IpcErrorCode.UNSUPPORTED_PROTOCOL,
            "IPC protocol version is not supported.",
            request_id,
        )
    if request_id == INVALID_REQUEST_ID:
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC request_id is invalid.",
        )
    command = value["command"]
    if not isinstance(command, str) or _COMMAND.fullmatch(command) is None:
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC command identifier is invalid.",
            request_id,
        )
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise IpcProtocolError(
            IpcErrorCode.INVALID_REQUEST,
            "IPC payload must be a JSON object.",
            request_id,
        )
    return IpcRequest(schema_version, request_id, command, payload)


def encode_response(response: IpcResponse) -> bytes:
    """Serialize one deterministic, bounded response line."""

    encoded = json.dumps(
        response.to_dict(),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_IPC_MESSAGE_BYTES:
        fallback = IpcResponse.failure(
            response.request_id,
            IpcErrorCode.INTERNAL_ERROR,
            "IPC response exceeds the maximum message size.",
        )
        return json.dumps(
            fallback.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return encoded
