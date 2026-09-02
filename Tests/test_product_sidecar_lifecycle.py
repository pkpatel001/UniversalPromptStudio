"""A-007 frozen-sidecar acceptance for portable items and redacted support data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from Backend.ipc import (
    APPLICATION_SETTINGS_GET_COMMAND,
    APPLICATION_SETTINGS_SAVE_COMMAND,
    DIAGNOSTICS_SNAPSHOT_COMMAND,
    PORTABILITY_EXPORT_COMMAND,
    PORTABILITY_IMPORT_COMMAND,
    PORTABILITY_PREVIEW_COMMAND,
    PROJECT_CREATE_COMMAND,
    PROMPT_CREATE_COMMAND,
    PROMPT_UPDATE_COMMAND,
    SUPPORT_EXPORT_COMMAND,
    SUPPORT_PREVIEW_COMMAND,
)
from Tests.test_sidecar_lifecycle import _command, _start, _stop
from Tests.test_sidecar_lifecycle import sidecar as sidecar


def test_frozen_sidecar_persists_settings_and_moves_only_reviewed_content(
    sidecar: Path,
    tmp_path: Path,
) -> None:
    source_data = tmp_path / "source-data"
    source = _start(sidecar, source_data)
    source_project = _result(
        _command(
            source,
            "source-project",
            PROJECT_CREATE_COMMAND,
            {"name": "Private source", "description": "Never exported"},
        )
    )["project"]
    project_id = _mapping(source_project)["project_id"]
    source_prompt = _result(
        _command(
            source,
            "source-prompt",
            PROMPT_CREATE_COMMAND,
            {"project_id": project_id, "title": "Portable acceptance"},
        )
    )["prompt"]
    prompt_id = _mapping(source_prompt)["prompt_id"]
    _command(
        source,
        "source-update",
        PROMPT_UPDATE_COMMAND,
        {
            "project_id": project_id,
            "prompt_id": prompt_id,
            "title": "Portable acceptance",
            "category": "Release",
            "tags": ["reviewed"],
            "blocks": [
                {
                    "block_type": "goal",
                    "content": "A-007 portable content",
                    "order": 0,
                    "enabled": True,
                }
            ],
            "confirm": True,
        },
    )
    portable = _result(
        _command(
            source,
            "portable-export",
            PORTABILITY_EXPORT_COMMAND,
            {"kind": "prompt", "item_id": prompt_id, "project_id": project_id},
        )
    )
    _stop(source)

    document = cast(str, portable["document"])
    assert "Private source" not in document
    assert "Never exported" not in document
    assert "credential" not in document

    target_data = tmp_path / "target-data"
    first = _start(sidecar, target_data)
    defaults = _result(
        _command(first, "settings-default", APPLICATION_SETTINGS_GET_COMMAND, {})
    )
    saved = _result(
        _command(
            first,
            "settings-save",
            APPLICATION_SETTINGS_SAVE_COMMAND,
            {
                "onboarding_completed": True,
                "compact_layout": True,
                "reduce_motion": True,
                "confirm": True,
            },
        )
    )
    target_project = _mapping(
        _result(
            _command(
                first,
                "target-project",
                PROJECT_CREATE_COMMAND,
                {"name": "Target", "description": ""},
            )
        )["project"]
    )
    target_project_id = target_project["project_id"]
    preview = _result(
        _command(
            first,
            "portable-preview",
            PORTABILITY_PREVIEW_COMMAND,
            {"document": document, "target_project_id": target_project_id},
        )
    )
    imported = _result(
        _command(
            first,
            "portable-import",
            PORTABILITY_IMPORT_COMMAND,
            {
                "document": document,
                "target_project_id": target_project_id,
                "expected_sha256": preview["document_sha256"],
                "resolution": "create",
                "confirm": True,
            },
        )
    )
    diagnostics = _result(
        _command(first, "diagnostics", DIAGNOSTICS_SNAPSHOT_COMMAND, {})
    )
    support_preview = _result(
        _command(first, "support-preview", SUPPORT_PREVIEW_COMMAND, {})
    )
    support_export = _result(
        _command(
            first,
            "support-export",
            SUPPORT_EXPORT_COMMAND,
            {
                "expected_sha256": support_preview["document_sha256"],
                "acknowledge_redaction_review": True,
                "confirm": True,
            },
        )
    )
    _stop(first)

    second = _start(sidecar, target_data)
    restarted = _result(
        _command(second, "settings-restarted", APPLICATION_SETTINGS_GET_COMMAND, {})
    )
    _stop(second)

    encoded_support = cast(str, support_export["document"])
    assert defaults["onboarding_completed"] is False
    assert saved["telemetry"] == "disabled"
    assert restarted == saved
    assert preview["allowed_resolutions"] == ["create"]
    assert imported["status"] == "created"
    assert diagnostics["library"] == {"project_count": 1, "prompt_count": 1}
    assert support_export["contains_credentials"] is False
    assert support_export["contains_user_content"] is False
    assert "Portable acceptance" not in encoded_support
    assert "A-007 portable content" not in encoded_support
    assert str(target_data) not in encoded_support
    assert json.loads(encoded_support)["format"] == "ups-redacted-support"


def _result(response: dict[str, object]) -> dict[str, object]:
    assert response["ok"] is True
    return _mapping(response["result"])


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)
