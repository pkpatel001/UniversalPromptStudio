"""Fixed IPC routes for A-007 product hardening operations."""

from __future__ import annotations

import re
from typing import cast
from uuid import UUID

from Backend.application.product_hardening import MAX_PORTABLE_DOCUMENT_CHARACTERS
from Backend.core.container import ApplicationContainer

from .models import IpcRequest, IpcResponse, JsonValue

APPLICATION_SETTINGS_GET_COMMAND = "application.settings.get"
APPLICATION_SETTINGS_SAVE_COMMAND = "application.settings.save"
PORTABILITY_EXPORT_COMMAND = "portability.export"
PORTABILITY_PREVIEW_COMMAND = "portability.preview"
PORTABILITY_IMPORT_COMMAND = "portability.import"
DIAGNOSTICS_SNAPSHOT_COMMAND = "diagnostics.snapshot"
SUPPORT_PREVIEW_COMMAND = "diagnostics.support.preview"
SUPPORT_EXPORT_COMMAND = "diagnostics.support.export"
PRODUCT_SUPPORTED_COMMANDS = (
    APPLICATION_SETTINGS_GET_COMMAND,
    APPLICATION_SETTINGS_SAVE_COMMAND,
    PORTABILITY_EXPORT_COMMAND,
    PORTABILITY_PREVIEW_COMMAND,
    PORTABILITY_IMPORT_COMMAND,
    DIAGNOSTICS_SNAPSHOT_COMMAND,
    SUPPORT_PREVIEW_COMMAND,
    SUPPORT_EXPORT_COMMAND,
)

_QUALIFIED_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def handle_product_command(container: ApplicationContainer, request: IpcRequest) -> IpcResponse:
    """Dispatch one allowlisted A-007 product command."""

    service = container.product_hardening_service
    if request.command == APPLICATION_SETTINGS_GET_COMMAND:
        _require_fields(request.payload, frozenset())
        result = service.settings()
    elif request.command == APPLICATION_SETTINGS_SAVE_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "onboarding_completed",
                    "compact_layout",
                    "reduce_motion",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["confirm"])
        result = service.save_settings(
            onboarding_completed=_boolean(request.payload["onboarding_completed"]),
            compact_layout=_boolean(request.payload["compact_layout"]),
            reduce_motion=_boolean(request.payload["reduce_motion"]),
        )
    elif request.command == PORTABILITY_EXPORT_COMMAND:
        _require_fields(request.payload, frozenset({"kind", "item_id", "project_id"}))
        kind = _kind(request.payload["kind"])
        result = service.export_item(
            kind,
            _item_id(request.payload["item_id"], kind),
            _optional_uuid(request.payload["project_id"]),
        )
    elif request.command == PORTABILITY_PREVIEW_COMMAND:
        _require_fields(request.payload, frozenset({"document", "target_project_id"}))
        result = service.preview_import(
            _document(request.payload["document"]),
            _optional_uuid(request.payload["target_project_id"]),
        )
    elif request.command == PORTABILITY_IMPORT_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "document",
                    "target_project_id",
                    "expected_sha256",
                    "resolution",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["confirm"])
        result = service.import_item(
            _document(request.payload["document"]),
            _optional_uuid(request.payload["target_project_id"]),
            _sha256(request.payload["expected_sha256"]),
            _resolution(request.payload["resolution"]),
        )
    elif request.command == DIAGNOSTICS_SNAPSHOT_COMMAND:
        _require_fields(request.payload, frozenset())
        result = service.diagnostics()
    elif request.command == SUPPORT_PREVIEW_COMMAND:
        _require_fields(request.payload, frozenset())
        result = service.support_preview()
    elif request.command == SUPPORT_EXPORT_COMMAND:
        _require_fields(
            request.payload,
            frozenset(
                {
                    "expected_sha256",
                    "acknowledge_redaction_review",
                    "confirm",
                }
            ),
        )
        _require_true(request.payload["acknowledge_redaction_review"])
        _require_true(request.payload["confirm"])
        result = service.export_support(_sha256(request.payload["expected_sha256"]))
    else:
        raise ValueError("Unsupported product command.")
    return IpcResponse.success(request.request_id, cast(dict[str, JsonValue], result))


def _require_fields(payload: dict[str, JsonValue], expected: frozenset[str]) -> None:
    if frozenset(payload) != expected:
        raise ValueError("Product payload fields are invalid.")


def _require_true(value: JsonValue) -> None:
    if value is not True:
        raise ValueError("Product operation requires explicit confirmation.")


def _boolean(value: JsonValue) -> bool:
    if type(value) is not bool:
        raise ValueError("Application preference is invalid.")
    return value


def _kind(value: JsonValue) -> str:
    if value not in {"prompt", "workflow"}:
        raise ValueError("Portable item kind is invalid.")
    return value


def _item_id(value: JsonValue, kind: str) -> str:
    if not isinstance(value, str) or len(value) > 128:
        raise ValueError("Portable item identity is invalid.")
    if kind == "prompt":
        return _uuid(value)
    if _QUALIFIED_ID.fullmatch(value) is None:
        raise ValueError("Workflow identity is invalid.")
    return value


def _uuid(value: str) -> str:
    try:
        canonical = str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Portable UUID is invalid.") from exc
    if value != canonical:
        raise ValueError("Portable UUID is not canonical.")
    return canonical


def _optional_uuid(value: JsonValue) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Portable project identity is invalid.")
    return _uuid(value)


def _document(value: JsonValue) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_PORTABLE_DOCUMENT_CHARACTERS:
        raise ValueError("Portable document is invalid or too large.")
    return value


def _sha256(value: JsonValue) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError("Portable SHA-256 is invalid.")
    return value


def _resolution(value: JsonValue) -> str:
    if value not in {"create", "skip", "replace"}:
        raise ValueError("Portable conflict resolution is invalid.")
    return value


__all__ = [
    "APPLICATION_SETTINGS_GET_COMMAND",
    "APPLICATION_SETTINGS_SAVE_COMMAND",
    "DIAGNOSTICS_SNAPSHOT_COMMAND",
    "PORTABILITY_EXPORT_COMMAND",
    "PORTABILITY_IMPORT_COMMAND",
    "PORTABILITY_PREVIEW_COMMAND",
    "PRODUCT_SUPPORTED_COMMANDS",
    "SUPPORT_EXPORT_COMMAND",
    "SUPPORT_PREVIEW_COMMAND",
    "handle_product_command",
]
