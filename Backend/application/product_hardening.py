"""A-007 portable-item, application-settings, and redacted diagnostics services."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

from Backend.application.customizations import ManagedCustomizationService
from Backend.application.provider_settings import ProviderConfigurationService
from Backend.application.services import (
    MAX_BLOCK_CONTENT_LENGTH,
    MAX_BLOCKS,
    MAX_CATEGORY_LENGTH,
    MAX_TAG_LENGTH,
    MAX_TAGS,
    MAX_TOTAL_BLOCK_CONTENT_LENGTH,
)
from Backend.application.workflows import (
    WorkflowAuthoringService,
    workflow_manifest_data,
    workflow_manifest_from_data,
)
from Backend.domain.models import Prompt, PromptBlock, PromptBlockType
from Backend.infrastructure.repositories.sqlite import CURRENT_SCHEMA_VERSION
from Backend.repositories.contracts import ProjectRepository, PromptRepository
from Engineering.core.version import VERSION

APPLICATION_SETTINGS_FILE_NAME = "application-settings.json"
PORTABLE_FORMAT = "ups-portable-item"
PORTABLE_SCHEMA_VERSION = 1
MAX_PORTABLE_DOCUMENT_CHARACTERS = 10_000
MAX_PORTABLE_RESULT_BYTES = 14_000
MAX_SETTINGS_BYTES = 4_096
SUPPORT_FORMAT = "ups-redacted-support"
SUPPORT_SCHEMA_VERSION = 1
_PROMPT_RESOLUTIONS = frozenset({"create", "skip", "replace"})
_WORKFLOW_RESOLUTIONS = frozenset({"create", "skip", "replace"})
_REDACTIONS = (
    "credentials",
    "prompt-content",
    "workflow-definitions-and-runtime-values",
    "filesystem-paths",
    "environment-values",
    "extension-code-and-contributions",
)


class ProductHardeningStorageError(RuntimeError):
    """Application-owned settings storage is unavailable or invalid."""


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    """Non-secret application preferences persisted below app data."""

    onboarding_completed: bool = False
    compact_layout: bool = False
    reduce_motion: bool = False


class ApplicationSettingsRepository:
    """Atomic exact-shape schema-1 settings repository."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("Application settings path must be absolute.")
        self._path = path

    def get(self) -> ApplicationSettings:
        if not self._path.exists():
            return ApplicationSettings()
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            raise ProductHardeningStorageError("Application settings are unavailable.") from exc
        try:
            if len(raw) > MAX_SETTINGS_BYTES:
                raise ValueError("Application settings are too large.")
            value = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
            root = _exact_mapping(value, {"schema_version", "settings"})
            if root["schema_version"] != 1:
                raise ValueError("Application settings schema is unsupported.")
            settings = _exact_mapping(
                root["settings"],
                {"onboarding_completed", "compact_layout", "reduce_motion"},
            )
            return ApplicationSettings(
                _boolean(settings["onboarding_completed"]),
                _boolean(settings["compact_layout"]),
                _boolean(settings["reduce_motion"]),
            )
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise ProductHardeningStorageError(
                "Application settings are invalid and were left unchanged."
            ) from exc

    def save(self, settings: ApplicationSettings) -> None:
        payload = _canonical_json(
            {
                "schema_version": 1,
                "settings": {
                    "onboarding_completed": settings.onboarding_completed,
                    "compact_layout": settings.compact_layout,
                    "reduce_motion": settings.reduce_motion,
                },
            }
        ).encode("utf-8")
        if len(payload) > MAX_SETTINGS_BYTES:
            raise ValueError("Application settings exceed the supported size.")
        _atomic_write(self._path, payload, ".application-settings-")


class ProductHardeningService:
    """Expose the final bounded local-product support workflows."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        prompt_repository: PromptRepository,
        workflow_service: WorkflowAuthoringService,
        provider_service: ProviderConfigurationService,
        customization_service: ManagedCustomizationService,
        app_data_directory: Path | None,
    ) -> None:
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        if app_data_directory is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="ups-product-")
            app_data_directory = Path(self._temporary.name)
        root = app_data_directory.resolve()
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise ProductHardeningStorageError("Application data is unavailable.")
        self._project_repository = project_repository
        self._prompt_repository = prompt_repository
        self._workflow_service = workflow_service
        self._provider_service = provider_service
        self._customization_service = customization_service
        self._settings = ApplicationSettingsRepository(root / APPLICATION_SETTINGS_FILE_NAME)

    def settings(self) -> dict[str, object]:
        """Return exact non-secret application preferences and fixed policy."""

        value = self._settings.get()
        return {
            "schema_version": 1,
            "onboarding_completed": value.onboarding_completed,
            "compact_layout": value.compact_layout,
            "reduce_motion": value.reduce_motion,
            "language": "en",
            "automatic_updates": "unsupported",
            "telemetry": "disabled",
        }

    def save_settings(
        self,
        *,
        onboarding_completed: bool,
        compact_layout: bool,
        reduce_motion: bool,
    ) -> dict[str, object]:
        """Atomically persist the complete exact-shape preference record."""

        self._settings.save(
            ApplicationSettings(
                onboarding_completed,
                compact_layout,
                reduce_motion,
            )
        )
        return self.settings()

    def export_item(self, kind: str, item_id: str, project_id: str | None) -> dict[str, object]:
        """Return one bounded portable item without a filesystem destination."""

        if kind == "prompt":
            if project_id is None:
                raise ValueError("Prompt export requires an owning project.")
            prompt = self._prompt_repository.get(_uuid(item_id))
            if prompt is None or prompt.project_id != _uuid(project_id):
                raise LookupError("Prompt does not exist in this project.")
            item = _prompt_data(prompt)
            title = prompt.title
            filename = f"ups-prompt-{prompt.prompt_id}.json"
        elif kind == "workflow":
            if project_id is not None:
                raise ValueError("Workflow export does not accept a project.")
            manifest = self._workflow_service.get(item_id)
            item = workflow_manifest_data(manifest)
            title = manifest.metadata.name
            filename = f"ups-workflow-{item_id}.json"
        else:
            raise ValueError("Portable item kind is unsupported.")
        document = _canonical_json(
            {
                "schema_version": PORTABLE_SCHEMA_VERSION,
                "format": PORTABLE_FORMAT,
                "kind": kind,
                "item": item,
            }
        )
        result = _export_result(kind, item_id, title, filename, document)
        if len(_canonical_json(result).encode("utf-8")) > MAX_PORTABLE_RESULT_BYTES:
            raise ValueError("This item exceeds the supported portable-file size.")
        return result

    def preview_import(self, document: str, target_project_id: str | None) -> dict[str, object]:
        """Revalidate one portable document and report explicit conflict choices."""

        parsed = self._parse_portable(document)
        kind = _text(parsed["kind"])
        if kind == "prompt":
            if target_project_id is None:
                raise ValueError("Prompt import requires a target project.")
            target = self._project_repository.get(_uuid(target_project_id))
            if target is None:
                raise LookupError("Target project does not exist.")
            prompt = _prompt_from_data(parsed["item"], target.project_id)
            existing_prompt = self._prompt_repository.get(prompt.prompt_id)
            if existing_prompt is None:
                conflict_state = "none"
                resolutions = ["create"]
            elif existing_prompt.project_id == target.project_id:
                conflict_state = "same-target"
                resolutions = ["skip", "replace"]
            else:
                conflict_state = "different-project"
                resolutions = ["skip"]
            item_id = prompt.prompt_id
            title = prompt.title
        else:
            if target_project_id is not None:
                raise ValueError("Workflow import does not accept a project.")
            manifest = workflow_manifest_from_data(parsed["item"])
            self._workflow_service.validate_definition(manifest)
            item_id = manifest.metadata.workflow_id.value
            title = manifest.metadata.name
            existing_workflow = next(
                (
                    item
                    for item in self._workflow_service.list()
                    if item.metadata.workflow_id.value == item_id
                ),
                None,
            )
            conflict_state = "none" if existing_workflow is None else "same-target"
            resolutions = ["create"] if existing_workflow is None else ["skip", "replace"]
        return {
            "schema_version": 1,
            "kind": kind,
            "item_id": item_id,
            "title": title,
            "target_project_id": target_project_id,
            "document_sha256": _sha256(document),
            "document_characters": len(document),
            "conflict_state": conflict_state,
            "allowed_resolutions": resolutions,
            "changes": ["prompt-definition" if kind == "prompt" else "workflow-definition"],
            "excluded": ["credentials", "execution-history", "extension-approval"],
        }

    def import_item(
        self,
        document: str,
        target_project_id: str | None,
        expected_sha256: str,
        resolution: str,
    ) -> dict[str, object]:
        """Apply only the exact re-previewed document and explicit resolution."""

        preview = self.preview_import(document, target_project_id)
        if preview["document_sha256"] != expected_sha256:
            raise ValueError("Portable document changed after preview.")
        allowed = preview["allowed_resolutions"]
        if not isinstance(allowed, list) or resolution not in allowed:
            raise ValueError("Portable conflict resolution is invalid.")
        kind = str(preview["kind"])
        item_id = str(preview["item_id"])
        title = str(preview["title"])
        if resolution == "skip":
            return {
                "kind": kind,
                "item_id": item_id,
                "title": title,
                "target_project_id": target_project_id,
                "applied": False,
                "status": "skipped",
            }
        parsed = self._parse_portable(document)
        if kind == "prompt":
            assert target_project_id is not None
            prompt = _prompt_from_data(parsed["item"], target_project_id)
            existing = self._prompt_repository.get(prompt.prompt_id)
            if resolution == "replace" and existing is not None:
                prompt.created_at = existing.created_at
            self._prompt_repository.add(prompt)
        else:
            manifest = workflow_manifest_from_data(parsed["item"])
            if resolution == "replace":
                self._workflow_service.update(item_id, manifest)
            else:
                self._workflow_service.create(manifest)
        return {
            "kind": kind,
            "item_id": item_id,
            "title": title,
            "target_project_id": target_project_id,
            "applied": True,
            "status": "replaced" if resolution == "replace" else "created",
        }

    def diagnostics(self) -> dict[str, object]:
        """Return presentation-safe counts and states without user content."""

        projects = tuple(self._project_repository.list())
        prompts = tuple(self._prompt_repository.list())
        workflows = self._workflow_service.list()
        providers = self._provider_service.catalog()
        customizations = self._customization_service.catalog()
        settings = self._settings.get()
        themes = customizations["themes"]
        extensions = customizations["extensions"]
        issues = customizations["issues"]
        assert isinstance(themes, list)
        assert isinstance(extensions, list)
        assert isinstance(issues, list)
        return {
            "schema_version": 1,
            "application": {
                "version": VERSION,
                "protocol_version": 1,
                "storage_schema_version": CURRENT_SCHEMA_VERSION,
                "platform": "windows-x64",
                "package": "nsis-current-user",
                "signed": False,
            },
            "library": {
                "project_count": len(projects),
                "prompt_count": len(prompts),
            },
            "workflows": {
                "definition_count": len(workflows),
                "operation_count": len(self._workflow_service.operations()),
            },
            "providers": [
                {
                    "provider_id": provider.provider_id,
                    "available": provider.available,
                    "credential_state": provider.credential_state,
                }
                for provider in providers
            ],
            "customizations": {
                "theme_count": len(themes),
                "active_theme_count": sum(
                    1 for item in themes if isinstance(item, dict) and item.get("state") == "active"
                ),
                "extension_count": len(extensions),
                "active_extension_count": sum(
                    1
                    for item in extensions
                    if isinstance(item, dict) and item.get("runtime_state") == "active"
                ),
                "issue_count": len(issues),
            },
            "preferences": {
                "onboarding_completed": settings.onboarding_completed,
                "compact_layout": settings.compact_layout,
                "reduce_motion": settings.reduce_motion,
            },
            "redactions": list(_REDACTIONS),
        }

    def support_preview(self) -> dict[str, object]:
        """Describe the exact redacted support document before export."""

        document = self._support_document()
        return {
            "schema_version": 1,
            "format": SUPPORT_FORMAT,
            "included_sections": [
                "application",
                "library-counts",
                "workflow-counts",
                "provider-availability",
                "customization-counts",
                "application-preferences",
            ],
            "redactions": list(_REDACTIONS),
            "contains_credentials": False,
            "contains_user_content": False,
            "document_sha256": _sha256(document),
            "document_characters": len(document),
        }

    def export_support(self, expected_sha256: str) -> dict[str, object]:
        """Return the exact reviewed redacted support document for download."""

        document = self._support_document()
        digest = _sha256(document)
        if digest != expected_sha256:
            raise ValueError("Support document changed after preview.")
        return {
            "filename": f"ups-support-{digest[:12]}.json",
            "document": document,
            "document_sha256": digest,
            "document_characters": len(document),
            "contains_credentials": False,
            "contains_user_content": False,
        }

    def _parse_portable(self, document: str) -> dict[str, object]:
        if (
            not isinstance(document, str)
            or not document
            or len(document) > MAX_PORTABLE_DOCUMENT_CHARACTERS
        ):
            raise ValueError("Portable document is invalid or too large.")
        try:
            value = json.loads(
                document,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("Portable document is invalid JSON.") from exc
        root = _exact_mapping(value, {"schema_version", "format", "kind", "item"})
        if (
            root["schema_version"] != PORTABLE_SCHEMA_VERSION
            or root["format"] != PORTABLE_FORMAT
            or root["kind"] not in {"prompt", "workflow"}
        ):
            raise ValueError("Portable document format is unsupported.")
        return root

    def _support_document(self) -> str:
        return _canonical_json(
            {
                "schema_version": SUPPORT_SCHEMA_VERSION,
                "format": SUPPORT_FORMAT,
                "diagnostics": self.diagnostics(),
                "redaction_review": {
                    "excluded": list(_REDACTIONS),
                    "contains_credentials": False,
                    "contains_user_content": False,
                },
            }
        )


def _export_result(
    kind: str, item_id: str, title: str, filename: str, document: str
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": kind,
        "item_id": item_id,
        "title": title,
        "filename": filename,
        "document": document,
        "document_sha256": _sha256(document),
        "document_characters": len(document),
        "excluded": ["credentials", "execution-history", "extension-approval"],
    }


def _prompt_data(prompt: Prompt) -> dict[str, object]:
    return {
        "prompt_id": prompt.prompt_id,
        "title": prompt.title,
        "category": prompt.category,
        "tags": sorted(prompt.tags, key=str.casefold),
        "blocks": [
            {
                "block_type": block.block_type.value,
                "content": block.content,
                "order": block.order,
                "enabled": block.enabled,
            }
            for block in sorted(prompt.blocks, key=lambda item: item.order)
        ],
    }


def _prompt_from_data(value: object, project_id: str) -> Prompt:
    item = _exact_mapping(value, {"prompt_id", "title", "category", "tags", "blocks"})
    prompt_id = _uuid(_text(item["prompt_id"]))
    title = _bounded_text(item["title"], 120, "Prompt title")
    category_value = item["category"]
    category = (
        None
        if category_value is None
        else _bounded_text(category_value, MAX_CATEGORY_LENGTH, "Prompt category")
    )
    tags_value = _bounded_list(item["tags"], MAX_TAGS)
    normalized_tags: dict[str, str] = {}
    for raw in tags_value:
        tag = _bounded_text(raw, MAX_TAG_LENGTH, "Prompt tag")
        if "\n" in tag or "\r" in tag or tag.casefold() in normalized_tags:
            raise ValueError("Prompt tags are invalid or duplicated.")
        normalized_tags[tag.casefold()] = tag
    blocks_value = _bounded_list(item["blocks"], MAX_BLOCKS)
    blocks: list[PromptBlock] = []
    total = 0
    for expected_order, raw in enumerate(blocks_value):
        block = _exact_mapping(raw, {"block_type", "content", "order", "enabled"})
        if _integer(block["order"]) != expected_order:
            raise ValueError("Portable prompt block order is invalid.")
        content = _bounded_text(block["content"], MAX_BLOCK_CONTENT_LENGTH, "Prompt block content")
        total += len(content)
        blocks.append(
            PromptBlock(
                PromptBlockType(_text(block["block_type"])),
                content,
                expected_order,
                _boolean(block["enabled"]),
            )
        )
    if total > MAX_TOTAL_BLOCK_CONTENT_LENGTH:
        raise ValueError("Portable prompt content exceeds the supported size.")
    now = datetime.now(UTC)
    return Prompt(
        title=title,
        project_id=_uuid(project_id),
        blocks=blocks,
        prompt_id=prompt_id,
        tags=set(normalized_tags.values()),
        category=category,
        created_at=now,
        updated_at=now,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _uuid(value: str) -> str:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Portable prompt identity is invalid.") from exc
    canonical = str(parsed)
    if canonical != value:
        raise ValueError("Portable prompt identity is not canonical.")
    return canonical


def _exact_mapping(value: object, keys: set[str]) -> dict[str, object]:
    if (
        not isinstance(value, dict)
        or not all(isinstance(key, str) for key in value)
        or set(value) != keys
    ):
        raise ValueError("Portable document fields are invalid.")
    return value


def _bounded_list(value: object, maximum: int) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError("Portable document collection is invalid.")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Portable document text is invalid.")
    return value


def _bounded_text(value: object, maximum: int, label: str) -> str:
    text = _text(value)
    if not text or text != text.strip() or len(text) > maximum:
        raise ValueError(f"{label} is invalid.")
    return text


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("Portable document integer is invalid.")
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("Portable document boolean is invalid.")
    return value


def _reject_constant(_value: str) -> NoReturn:
    raise ValueError("Non-finite values are not supported.")


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON fields are not supported.")
        value[key] = item
    return value


def _atomic_write(path: Path, payload: bytes, prefix: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=prefix,
            suffix=".tmp",
            dir=path.parent,
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
    except OSError as exc:
        raise ProductHardeningStorageError("Application settings are unavailable.") from exc


__all__ = [
    "APPLICATION_SETTINGS_FILE_NAME",
    "ApplicationSettings",
    "ApplicationSettingsRepository",
    "MAX_PORTABLE_DOCUMENT_CHARACTERS",
    "PORTABLE_FORMAT",
    "ProductHardeningService",
    "ProductHardeningStorageError",
    "SUPPORT_FORMAT",
]
