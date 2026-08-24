"""Closed application-owned command router for A-001.1."""

from __future__ import annotations

from collections.abc import Callable

from Backend.core.container import ApplicationContainer, create_in_memory_container
from Engineering.core.version import VERSION

from .models import IPC_PROTOCOL_VERSION, IpcErrorCode, IpcRequest, IpcResponse, JsonValue

APPLICATION_READINESS_COMMAND = "application.readiness"
SUPPORTED_COMMANDS = (APPLICATION_READINESS_COMMAND,)


class ApplicationIpcRouter:
    """Route validated requests through one long-lived application container."""

    def __init__(
        self,
        container_factory: Callable[[], ApplicationContainer] = create_in_memory_container,
    ) -> None:
        self._container = container_factory()

    def handle(self, request: IpcRequest) -> IpcResponse:
        if request.command != APPLICATION_READINESS_COMMAND:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.UNKNOWN_COMMAND,
                "IPC command is not supported.",
            )
        if request.payload:
            return IpcResponse.failure(
                request.request_id,
                IpcErrorCode.INVALID_PAYLOAD,
                "Application readiness does not accept payload fields.",
            )
        result: dict[str, JsonValue] = {
            "status": "ready",
            "application_version": VERSION,
            "protocol_version": IPC_PROTOCOL_VERSION,
            "capabilities": list(SUPPORTED_COMMANDS),
        }
        return IpcResponse.success(request.request_id, result)

