"""Fixed IPC routes for A-006 managed customization lifecycle operations."""

from __future__ import annotations

import re
from typing import cast

from Backend.core.container import ApplicationContainer

from .models import IpcRequest, IpcResponse, JsonValue

CUSTOMIZATION_CATALOG_COMMAND = "customizations.catalog"
THEME_INSTALL_COMMAND = "themes.install"
THEME_LIFECYCLE_COMMAND = "themes.lifecycle"
EXTENSION_ACTIVATE_COMMAND = "extensions.activate"
EXTENSION_DEACTIVATE_COMMAND = "extensions.deactivate"
CUSTOMIZATION_SUPPORTED_COMMANDS = (
    CUSTOMIZATION_CATALOG_COMMAND,
    THEME_INSTALL_COMMAND,
    THEME_LIFECYCLE_COMMAND,
    EXTENSION_ACTIVATE_COMMAND,
    EXTENSION_DEACTIVATE_COMMAND,
)

_QUALIFIED_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$")
_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def handle_customization_command(
    container: ApplicationContainer, request: IpcRequest
) -> IpcResponse:
    """Dispatch one allowlisted customization command."""

    service = container.customization_service
    if request.command == CUSTOMIZATION_CATALOG_COMMAND:
        _require_fields(request.payload, frozenset())
        result = service.catalog()
    elif request.command == THEME_INSTALL_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "package_filename",
                    "approved_sha256",
                    "acknowledge_external_theme",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["confirm"])
        result = service.install_theme(
            _package_filename(request.payload["package_filename"]),
            _sha256(request.payload["approved_sha256"]),
            acknowledge_external_theme=_required_bool(
                request.payload["acknowledge_external_theme"]
            ),
        )
    elif request.command == THEME_LIFECYCLE_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "theme_id",
                    "version",
                    "action",
                    "approved_package_sha256",
                    "acknowledge_lifecycle_change",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["confirm"])
        action = request.payload["action"]
        if action not in ("disable", "restore"):
            raise ValueError("Unsupported theme lifecycle action.")
        result = service.change_theme_state(
            _qualified_id(request.payload["theme_id"]),
            _version(request.payload["version"]),
            action,
            _sha256(request.payload["approved_package_sha256"]),
            acknowledge_lifecycle_change=_required_bool(
                request.payload["acknowledge_lifecycle_change"]
            ),
        )
    elif request.command == EXTENSION_ACTIVATE_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "plugin_id",
                    "version",
                    "directory_sha256",
                    "acknowledge_full_trust",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["confirm"])
        result = service.activate_extension(
            _qualified_id(request.payload["plugin_id"]),
            _version(request.payload["version"]),
            _sha256(request.payload["directory_sha256"]),
            acknowledge_full_trust=_required_bool(request.payload["acknowledge_full_trust"]),
        )
    elif request.command == EXTENSION_DEACTIVATE_COMMAND:
        _require_fields(
            request.payload,
            frozenset({"plugin_id", "version", "directory_sha256", "confirm"}),
        )
        _require_true(request.payload["confirm"])
        result = service.deactivate_extension(
            _qualified_id(request.payload["plugin_id"]),
            _version(request.payload["version"]),
            _sha256(request.payload["directory_sha256"]),
        )
    else:
        raise ValueError("Unsupported customization command.")
    return IpcResponse.success(request.request_id, cast(dict[str, JsonValue], result))


def _require_fields(payload: dict[str, JsonValue], expected: frozenset[str]) -> None:
    if frozenset(payload) != expected:
        raise ValueError("Customization payload fields are invalid.")


def _required_bool(value: JsonValue) -> bool:
    if type(value) is not bool:
        raise ValueError("Customization acknowledgement is invalid.")
    return value


def _require_true(value: JsonValue) -> None:
    if value is not True:
        raise ValueError("Customization operation requires confirmation.")


def _qualified_id(value: JsonValue) -> str:
    if not isinstance(value, str) or len(value) > 128 or not _QUALIFIED_ID.fullmatch(value):
        raise ValueError("Customization identity is invalid.")
    return value


def _version(value: JsonValue) -> str:
    if not isinstance(value, str) or len(value) > 64 or not _VERSION.fullmatch(value):
        raise ValueError("Customization version is invalid.")
    return value


def _sha256(value: JsonValue) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("Customization SHA-256 is invalid.")
    return value


def _package_filename(value: JsonValue) -> str:
    if (
        not isinstance(value, str)
        or not value.endswith(".ups-theme.zip")
        or len(value) > 240
        or "/" in value
        or "\\" in value
    ):
        raise ValueError("Theme package filename is invalid.")
    return value


__all__ = [
    "CUSTOMIZATION_CATALOG_COMMAND",
    "CUSTOMIZATION_SUPPORTED_COMMANDS",
    "EXTENSION_ACTIVATE_COMMAND",
    "EXTENSION_DEACTIVATE_COMMAND",
    "THEME_INSTALL_COMMAND",
    "THEME_LIFECYCLE_COMMAND",
    "handle_customization_command",
]
