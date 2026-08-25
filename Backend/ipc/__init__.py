"""Bounded application IPC contracts and server."""

from .models import (
    IPC_PROTOCOL_VERSION,
    MAX_IPC_MESSAGE_BYTES,
    IpcError,
    IpcErrorCode,
    IpcRequest,
    IpcResponse,
)
from .protocol import IpcProtocolError, encode_response, parse_request
from .router import APPLICATION_READINESS_COMMAND, SIDECAR_IDENTITY, ApplicationIpcRouter
from .server import IpcServer, serve_stdio

__all__ = [
    "APPLICATION_READINESS_COMMAND",
    "IPC_PROTOCOL_VERSION",
    "MAX_IPC_MESSAGE_BYTES",
    "SIDECAR_IDENTITY",
    "ApplicationIpcRouter",
    "IpcError",
    "IpcErrorCode",
    "IpcProtocolError",
    "IpcRequest",
    "IpcResponse",
    "IpcServer",
    "encode_response",
    "parse_request",
    "serve_stdio",
]
