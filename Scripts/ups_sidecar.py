"""Frozen entrypoint for the Universal Prompt Studio application sidecar."""

from __future__ import annotations

import json
import sys

from Backend.ipc import IPC_PROTOCOL_VERSION, SIDECAR_IDENTITY, serve_stdio
from Engineering.core.version import VERSION


def main(arguments: list[str] | None = None) -> int:
    """Run the stdio server or print the exact build identity."""

    selected = list(sys.argv[1:] if arguments is None else arguments)
    if selected == ["--identity"]:
        print(
            json.dumps(
                {
                    "application_version": VERSION,
                    "protocol_version": IPC_PROTOCOL_VERSION,
                    "sidecar_identity": SIDECAR_IDENTITY,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    if selected:
        return 64
    return serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
