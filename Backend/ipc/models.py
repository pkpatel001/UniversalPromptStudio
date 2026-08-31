"""Immutable A-001.1 IPC request, response, and failure values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IPC_PROTOCOL_VERSION = 1
MAX_IPC_MESSAGE_BYTES = 16_384

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class IpcErrorCode(StrEnum):
    """Stable safe failure codes crossing the desktop IPC boundary."""

    INVALID_REQUEST = "ipc.invalid_request"
    MESSAGE_TOO_LARGE = "ipc.message_too_large"
    UNSUPPORTED_PROTOCOL = "ipc.unsupported_protocol"
    UNKNOWN_COMMAND = "ipc.unknown_command"
    INVALID_PAYLOAD = "ipc.invalid_payload"
    INTERNAL_ERROR = "ipc.internal_error"
    NOT_FOUND = "library.not_found"
    STORAGE_UNAVAILABLE = "storage.unavailable"
    INVALID_DATABASE = "storage.invalid_database"
    FUTURE_SCHEMA = "storage.future_schema"


@dataclass(frozen=True, slots=True)
class IpcError:
    """Safe structured IPC failure without exception or environment detail."""

    code: IpcErrorCode
    message: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"code": self.code.value, "message": self.message}


@dataclass(frozen=True, slots=True)
class IpcRequest:
    """One validated protocol request."""

    schema_version: int
    request_id: str
    command: str
    payload: dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class IpcResponse:
    """One correlated success or failure response."""

    request_id: str
    result: dict[str, JsonValue] | None = None
    error: IpcError | None = None

    @classmethod
    def success(cls, request_id: str, result: dict[str, JsonValue]) -> IpcResponse:
        return cls(request_id=request_id, result=result)

    @classmethod
    def failure(
        cls,
        request_id: str,
        code: IpcErrorCode,
        message: str,
    ) -> IpcResponse:
        return cls(request_id=request_id, error=IpcError(code, message))

    def to_dict(self) -> dict[str, JsonValue]:
        if (self.result is None) == (self.error is None):
            raise ValueError("IPC response must contain exactly one result or error.")
        encoded: dict[str, JsonValue] = {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": self.request_id,
            "ok": self.error is None,
        }
        if self.error is None:
            encoded["result"] = self.result
        else:
            encoded["error"] = self.error.to_dict()
        return encoded
