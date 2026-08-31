"""Long-lived, bounded standard-stream IPC server."""

from __future__ import annotations

import sys
from typing import BinaryIO

from Backend.core.container import create_desktop_container

from .models import MAX_IPC_MESSAGE_BYTES, IpcErrorCode, IpcResponse
from .protocol import INVALID_REQUEST_ID, IpcProtocolError, encode_response, parse_request
from .router import ApplicationIpcRouter


class IpcServer:
    """Serve correlated request/response lines until the host closes stdin."""

    def __init__(self, router: ApplicationIpcRouter | None = None) -> None:
        self._router = router or ApplicationIpcRouter()

    def run(self, input_stream: BinaryIO, output_stream: BinaryIO) -> int:
        while True:
            raw = input_stream.readline(MAX_IPC_MESSAGE_BYTES + 2)
            if raw == b"":
                return 0
            oversized = len(raw) > MAX_IPC_MESSAGE_BYTES + 1 or (
                len(raw) == MAX_IPC_MESSAGE_BYTES + 1 and not raw.endswith(b"\n")
            )
            if oversized:
                self._drain_line(input_stream, raw)
                response = IpcResponse.failure(
                    INVALID_REQUEST_ID,
                    IpcErrorCode.MESSAGE_TOO_LARGE,
                    "IPC request exceeds the maximum message size.",
                )
            else:
                line = raw[:-1] if raw.endswith(b"\n") else raw
                if line.endswith(b"\r"):
                    line = line[:-1]
                response = self._handle_line(line)
            output_stream.write(encode_response(response) + b"\n")
            output_stream.flush()

    def _handle_line(self, raw: bytes) -> IpcResponse:
        try:
            request = parse_request(raw)
            return self._router.handle(request)
        except IpcProtocolError as exc:
            return exc.to_response()
        except Exception:
            return IpcResponse.failure(
                INVALID_REQUEST_ID,
                IpcErrorCode.INTERNAL_ERROR,
                "IPC request failed safely.",
            )

    @staticmethod
    def _drain_line(input_stream: BinaryIO, initial: bytes) -> None:
        if initial.endswith(b"\n"):
            return
        while True:
            remainder = input_stream.readline(MAX_IPC_MESSAGE_BYTES + 2)
            if remainder == b"" or remainder.endswith(b"\n"):
                return


def serve_stdio() -> int:
    """Create one application container and serve the host until EOF."""

    router = ApplicationIpcRouter(create_desktop_container)
    return IpcServer(router).run(sys.stdin.buffer, sys.stdout.buffer)
