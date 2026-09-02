"""A-007 portability, settings, diagnostics, and onboarding boundary tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from Backend.application.product_hardening import (
    APPLICATION_SETTINGS_FILE_NAME,
    MAX_PORTABLE_DOCUMENT_CHARACTERS,
    ProductHardeningStorageError,
)
from Backend.application.workflows import workflow_manifest_from_data
from Backend.core.container import ApplicationContainer, create_sqlite_container
from Backend.domain.models import PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import DATABASE_FILE_NAME
from Backend.ipc.models import IPC_PROTOCOL_VERSION, IpcRequest, JsonValue
from Backend.ipc.product_routes import (
    APPLICATION_SETTINGS_GET_COMMAND,
    APPLICATION_SETTINGS_SAVE_COMMAND,
    DIAGNOSTICS_SNAPSHOT_COMMAND,
    PORTABILITY_IMPORT_COMMAND,
    PORTABILITY_PREVIEW_COMMAND,
    SUPPORT_EXPORT_COMMAND,
    SUPPORT_PREVIEW_COMMAND,
)
from Backend.ipc.router import ApplicationIpcRouter


def _container(root: Path) -> ApplicationContainer:
    return create_sqlite_container(root / DATABASE_FILE_NAME)


def _request(command: str, payload: dict[str, JsonValue]) -> IpcRequest:
    return IpcRequest(
        IPC_PROTOCOL_VERSION,
        f"a007-{command}",
        command,
        payload,
    )


def _echo_workflow() -> dict[str, object]:
    node_input = {
        "id": "value",
        "type": "string",
        "description": "Text supplied to the operation.",
    }
    node_output = {
        "id": "value",
        "type": "string",
        "description": "Text returned by the operation.",
    }
    return {
        "schema_version": 1,
        "workflow": {
            "id": "ups.user-echo",
            "name": "User Echo",
            "version": "1.0.0",
            "sdk_version": 1,
            "description": "Durable user-authored offline echo workflow.",
            "inputs": [{"id": "input", "type": "string", "description": "Workflow text."}],
            "outputs": [{"id": "output", "type": "string", "description": "Workflow result."}],
            "nodes": [
                {
                    "id": "echo",
                    "operation": "ups.echo-text",
                    "inputs": [node_input],
                    "outputs": [node_output],
                }
            ],
            "edges": [
                {
                    "source": {"workflow_input": "input"},
                    "target": {"node": "echo", "port": "value"},
                },
                {
                    "source": {"node": "echo", "port": "value"},
                    "target": {"workflow_output": "output"},
                },
            ],
        },
    }


def test_application_settings_are_exact_atomic_non_secret_and_restart_safe(
    tmp_path: Path,
) -> None:
    first = _container(tmp_path)

    saved = first.product_hardening_service.save_settings(
        onboarding_completed=True,
        compact_layout=True,
        reduce_motion=True,
    )
    second = _container(tmp_path)
    path = tmp_path / APPLICATION_SETTINGS_FILE_NAME
    document = json.loads(path.read_text(encoding="utf-8"))

    assert saved["onboarding_completed"] is True
    assert second.product_hardening_service.settings() == saved
    assert document == {
        "schema_version": 1,
        "settings": {
            "compact_layout": True,
            "onboarding_completed": True,
            "reduce_motion": True,
        },
    }
    assert "credential" not in path.read_text(encoding="utf-8")


def test_invalid_application_settings_fail_without_repair(tmp_path: Path) -> None:
    path = tmp_path / APPLICATION_SETTINGS_FILE_NAME
    path.write_text('{"schema_version":2,"settings":{}}', encoding="utf-8")
    original = path.read_bytes()

    with pytest.raises(ProductHardeningStorageError):
        _container(tmp_path).product_hardening_service.settings()

    assert path.read_bytes() == original


def test_prompt_export_preview_import_and_explicit_conflict_resolution(
    tmp_path: Path,
) -> None:
    source = _container(tmp_path / "source")
    project = source.project_service.create_project("Source")
    prompt = source.prompt_service.create_library_prompt(project.project_id, "Portable prompt")
    source.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        "Portable prompt",
        "Delivery",
        ["Reviewed"],
        [PromptBlock(PromptBlockType.GOAL, "Ship safely.", 0)],
    )
    exported = source.product_hardening_service.export_item(
        "prompt", prompt.prompt_id, project.project_id
    )

    target = _container(tmp_path / "target")
    target_project = target.project_service.create_project("Target")
    preview = target.product_hardening_service.preview_import(
        cast(str, exported["document"]), target_project.project_id
    )
    created = target.product_hardening_service.import_item(
        cast(str, exported["document"]),
        target_project.project_id,
        cast(str, exported["document_sha256"]),
        "create",
    )
    conflict = target.product_hardening_service.preview_import(
        cast(str, exported["document"]), target_project.project_id
    )
    skipped = target.product_hardening_service.import_item(
        cast(str, exported["document"]),
        target_project.project_id,
        cast(str, exported["document_sha256"]),
        "skip",
    )

    imported = target.prompt_service.get_project_prompt(target_project.project_id, prompt.prompt_id)
    assert preview["conflict_state"] == "none"
    assert preview["allowed_resolutions"] == ["create"]
    assert created["status"] == "created"
    assert imported.title == "Portable prompt"
    assert imported.category == "Delivery"
    assert imported.tags == {"Reviewed"}
    assert imported.blocks[0].content == "Ship safely."
    assert conflict["allowed_resolutions"] == ["skip", "replace"]
    assert skipped["applied"] is False and skipped["status"] == "skipped"
    assert "Source" not in cast(str, exported["document"])


def test_prompt_identity_in_another_project_cannot_be_silently_moved(
    tmp_path: Path,
) -> None:
    container = _container(tmp_path)
    source = container.project_service.create_project("Source")
    target = container.project_service.create_project("Target")
    prompt = container.prompt_service.create_library_prompt(source.project_id, "Owned")
    exported = container.product_hardening_service.export_item(
        "prompt", prompt.prompt_id, source.project_id
    )

    preview = container.product_hardening_service.preview_import(
        cast(str, exported["document"]), target.project_id
    )

    assert preview["conflict_state"] == "different-project"
    assert preview["allowed_resolutions"] == ["skip"]
    with pytest.raises(ValueError):
        container.product_hardening_service.import_item(
            cast(str, exported["document"]),
            target.project_id,
            cast(str, exported["document_sha256"]),
            "replace",
        )
    existing = container.prompt_repository.get(prompt.prompt_id)
    assert existing is not None
    assert existing.project_id == source.project_id


def test_workflow_export_import_reuses_trusted_definition_validation(
    tmp_path: Path,
) -> None:
    source = _container(tmp_path / "source")
    manifest = workflow_manifest_from_data(_echo_workflow())
    source.workflow_authoring_service.create(manifest)
    exported = source.product_hardening_service.export_item("workflow", "ups.user-echo", None)
    target = _container(tmp_path / "target")

    preview = target.product_hardening_service.preview_import(cast(str, exported["document"]), None)
    result = target.product_hardening_service.import_item(
        cast(str, exported["document"]),
        None,
        cast(str, exported["document_sha256"]),
        "create",
    )

    assert preview["kind"] == "workflow"
    assert preview["changes"] == ["workflow-definition"]
    assert result["status"] == "created"
    assert target.workflow_authoring_service.get("ups.user-echo").metadata.name == "User Echo"


def test_diagnostics_and_support_export_are_content_free_and_digest_bound(
    tmp_path: Path,
) -> None:
    container = _container(tmp_path)
    project = container.project_service.create_project("Secret project name")
    prompt = container.prompt_service.create_library_prompt(project.project_id, "Private title")
    container.prompt_service.update_library_prompt(
        project.project_id,
        prompt.prompt_id,
        "Private title",
        None,
        [],
        [PromptBlock(PromptBlockType.CONTEXT, "private prompt content", 0)],
    )

    snapshot = container.product_hardening_service.diagnostics()
    preview = container.product_hardening_service.support_preview()
    exported = container.product_hardening_service.export_support(
        cast(str, preview["document_sha256"])
    )
    encoded = json.dumps(exported, sort_keys=True)

    assert snapshot["library"] == {"project_count": 1, "prompt_count": 1}
    assert preview["contains_credentials"] is False
    assert preview["contains_user_content"] is False
    assert "Private title" not in encoded
    assert "private prompt content" not in encoded
    assert str(tmp_path) not in encoded
    assert cast(str, exported["filename"]).startswith("ups-support-")


def test_product_ipc_requires_exact_fields_review_and_confirmation(
    tmp_path: Path,
) -> None:
    router = ApplicationIpcRouter(lambda: create_sqlite_container(tmp_path / DATABASE_FILE_NAME))
    settings = router.handle(_request(APPLICATION_SETTINGS_GET_COMMAND, {}))
    unconfirmed = router.handle(
        _request(
            APPLICATION_SETTINGS_SAVE_COMMAND,
            {
                "onboarding_completed": True,
                "compact_layout": False,
                "reduce_motion": False,
                "confirm": False,
            },
        )
    )
    snapshot = router.handle(_request(DIAGNOSTICS_SNAPSHOT_COMMAND, {}))
    support = router.handle(_request(SUPPORT_PREVIEW_COMMAND, {}))
    digest = cast(str, cast(dict[str, object], support.result)["document_sha256"])
    unreviewed = router.handle(
        _request(
            SUPPORT_EXPORT_COMMAND,
            {
                "expected_sha256": digest,
                "acknowledge_redaction_review": False,
                "confirm": True,
            },
        )
    )

    assert settings.error is None
    assert snapshot.error is None
    assert unconfirmed.error is not None
    assert unconfirmed.error.code.value == "ipc.invalid_payload"
    assert unreviewed.error is not None
    assert unreviewed.error.code.value == "ipc.invalid_payload"


@pytest.mark.parametrize(
    "document",
    [
        "",
        "x" * (MAX_PORTABLE_DOCUMENT_CHARACTERS + 1),
        '{"schema_version":1,"schema_version":1}',
        '{"schema_version":NaN,"format":"ups-portable-item","kind":"prompt","item":{}}',
    ],
)
def test_portable_documents_reject_malformed_duplicate_nonfinite_and_oversized_input(
    tmp_path: Path, document: str
) -> None:
    service = _container(tmp_path).product_hardening_service

    with pytest.raises(ValueError):
        service.preview_import(document, None)


def test_portability_ipc_rejects_unknown_resolution_and_unconfirmed_apply(
    tmp_path: Path,
) -> None:
    container = _container(tmp_path)
    project = container.project_service.create_project("Target")
    router = ApplicationIpcRouter(lambda: container)
    document = json.dumps(
        {
            "schema_version": 1,
            "format": "ups-portable-item",
            "kind": "prompt",
            "item": {
                "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Portable",
                "category": None,
                "tags": [],
                "blocks": [],
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    preview = router.handle(
        _request(
            PORTABILITY_PREVIEW_COMMAND,
            {"document": document, "target_project_id": project.project_id},
        )
    )
    digest = cast(str, cast(dict[str, object], preview.result)["document_sha256"])
    response = router.handle(
        _request(
            PORTABILITY_IMPORT_COMMAND,
            {
                "document": document,
                "target_project_id": project.project_id,
                "expected_sha256": digest,
                "resolution": "create",
                "confirm": False,
            },
        )
    )

    assert response.error is not None
    assert response.error.code.value == "ipc.invalid_payload"
