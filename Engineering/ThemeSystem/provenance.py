"""Strict E-015.8 provenance receipts and managed-theme integrity verification."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from Engineering.core.exceptions import ThemeError

from .manifest import THEME_MANIFEST_NAME, ThemeManifestReader
from .models import ThemeId, ThemeManifest, ThemeVersion
from .package import MAX_THEME_MANIFEST_BYTES, THEME_PACKAGE_SUFFIX

THEME_INSTALLATION_RECEIPT_NAME = "theme-installation.json"
THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION = 1
THEME_MANAGED_DIRECTORY = "Installed"
THEME_DISABLED_DIRECTORY = ".ups-theme-disabled"
THEME_TRUST_POLICY_ID = "explicit-external-theme-sha256-v1"
MAX_THEME_RECEIPT_BYTES = 64 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_ROOT_KEYS = frozenset({"schema_version", "theme", "source", "content", "trust"})
_THEME_KEYS = frozenset({"id", "version"})
_SOURCE_KEYS = frozenset({"label", "package_filename", "package_sha256"})
_CONTENT_KEYS = frozenset({THEME_MANIFEST_NAME})
_CONTENT_ENTRY_KEYS = frozenset({"sha256", "size"})
_TRUST_KEYS = frozenset(
    {"policy", "approved_sha256", "external_theme_acknowledged"}
)


class ThemeManagedState(StrEnum):
    """Host-owned lifecycle location for an installed theme."""

    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ThemeInstallationReceipt:
    """Validated deterministic schema-1 installation provenance."""

    theme_id: ThemeId
    version: ThemeVersion
    source_label: str
    package_filename: str
    package_sha256: str
    manifest_sha256: str
    manifest_size: int
    trust_policy: str
    approved_sha256: str
    external_theme_acknowledged: bool


@dataclass(frozen=True, slots=True)
class ThemeManagedRecord:
    """One exact managed installation whose receipt and manifest agree."""

    state: ThemeManagedState
    relative_path: str
    manifest: ThemeManifest
    receipt: ThemeInstallationReceipt
    root_id: str = "project"

    @property
    def theme_id(self) -> str:
        return self.manifest.metadata.theme_id.value

    @property
    def version(self) -> str:
        return self.manifest.metadata.version.value


@dataclass(frozen=True, slots=True)
class ThemeManagedIssue:
    """One deterministic managed-theme integrity or layout problem."""

    state: ThemeManagedState
    relative_path: str
    code: str
    message: str
    root_id: str = "project"


@dataclass(frozen=True, slots=True)
class ThemeManagedVerificationReport:
    """Aggregate verification for active and disabled managed themes."""

    records: tuple[ThemeManagedRecord, ...] = ()
    issues: tuple[ThemeManagedIssue, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.issues

    @property
    def summary(self) -> str:
        state = "succeeded" if self.passed else "failed"
        return (
            f"Managed theme verification {state}: {len(self.records)} verified, "
            f"{len(self.issues)} issues."
        )


def validate_theme_source_label(value: str) -> None:
    """Validate a bounded caller-supplied provenance label."""

    if (
        not isinstance(value, str)
        or value.strip() != value
        or not value
        or len(value) > 240
        or any(ord(character) < 32 for character in value)
    ):
        raise ThemeError(
            "Theme source label must be 1-240 trimmed characters without controls."
        )


def validate_theme_sha256(value: object, label: str) -> str:
    """Return one canonical lowercase SHA-256 value or fail."""

    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ThemeError(f"{label} must be 64 lowercase hexadecimal characters.")
    return value


class ThemeInstallationReceiptReader:
    """Read an exact bounded JSON receipt without accepting duplicate keys."""

    def read(self, path: Path) -> ThemeInstallationReceipt:
        if path.is_symlink():
            raise ThemeError("Theme installation receipt must not be a symlink.")
        if not path.is_file():
            raise ThemeError(f"Managed theme is missing {THEME_INSTALLATION_RECEIPT_NAME}.")
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_THEME_RECEIPT_BYTES + 1)
        except OSError as exc:
            raise ThemeError("Theme installation receipt could not be read.") from exc
        if len(content) > MAX_THEME_RECEIPT_BYTES:
            raise ThemeError("Theme installation receipt exceeds the size limit.")
        try:
            text = content.decode("utf-8")
            data = json.loads(text, object_pairs_hook=self._unique_object)
        except UnicodeDecodeError as exc:
            raise ThemeError("Theme installation receipt must be UTF-8 JSON.") from exc
        except json.JSONDecodeError as exc:
            raise ThemeError("Theme installation receipt JSON is malformed.") from exc
        except ValueError as exc:
            raise ThemeError(str(exc)) from exc
        return self._parse(data)

    def _parse(self, value: object) -> ThemeInstallationReceipt:
        root = self._mapping(value, "Theme installation receipt")
        self._exact_keys(root, _RECEIPT_ROOT_KEYS, "Theme installation receipt")
        if type(root["schema_version"]) is not int:
            raise ThemeError("Theme installation receipt schema_version must be an integer.")
        if root["schema_version"] != THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION:
            raise ThemeError("Unsupported theme installation receipt schema_version.")

        theme = self._mapping(root["theme"], "receipt.theme")
        source = self._mapping(root["source"], "receipt.source")
        content = self._mapping(root["content"], "receipt.content")
        trust = self._mapping(root["trust"], "receipt.trust")
        self._exact_keys(theme, _THEME_KEYS, "receipt.theme")
        self._exact_keys(source, _SOURCE_KEYS, "receipt.source")
        self._exact_keys(content, _CONTENT_KEYS, "receipt.content")
        self._exact_keys(trust, _TRUST_KEYS, "receipt.trust")

        theme_id = ThemeId(self._string(theme["id"], "receipt.theme.id"))
        version = ThemeVersion(self._string(theme["version"], "receipt.theme.version"))
        source_label = self._string(source["label"], "receipt.source.label")
        validate_theme_source_label(source_label)
        package_filename = self._string(
            source["package_filename"], "receipt.source.package_filename"
        )
        expected_filename = f"{theme_id.value}-{version.value}{THEME_PACKAGE_SUFFIX}"
        if package_filename != expected_filename:
            raise ThemeError(
                f"Receipt package filename must match theme identity: {expected_filename}."
            )
        package_sha256 = validate_theme_sha256(
            source["package_sha256"], "Receipt package SHA-256"
        )

        entry = self._mapping(content[THEME_MANIFEST_NAME], "receipt.content manifest")
        self._exact_keys(entry, _CONTENT_ENTRY_KEYS, "receipt.content manifest")
        manifest_sha256 = validate_theme_sha256(
            entry["sha256"], "Receipt manifest SHA-256"
        )
        manifest_size = entry["size"]
        if (
            type(manifest_size) is not int
            or manifest_size < 1
            or manifest_size > MAX_THEME_MANIFEST_BYTES
        ):
            raise ThemeError("Receipt manifest size is outside the supported range.")

        policy = self._string(trust["policy"], "receipt.trust.policy")
        if policy != THEME_TRUST_POLICY_ID:
            raise ThemeError(f"Unsupported theme trust policy: {policy!r}.")
        approved_sha256 = validate_theme_sha256(
            trust["approved_sha256"], "Receipt approved SHA-256"
        )
        if approved_sha256 != package_sha256:
            raise ThemeError("Receipt approved SHA-256 does not match package SHA-256.")
        acknowledged = trust["external_theme_acknowledged"]
        if acknowledged is not True:
            raise ThemeError("Receipt must record explicit external-theme acknowledgement.")
        return ThemeInstallationReceipt(
            theme_id,
            version,
            source_label,
            package_filename,
            package_sha256,
            manifest_sha256,
            manifest_size,
            policy,
            approved_sha256,
            True,
        )

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Theme installation receipt contains duplicate key: {key}.")
            result[key] = value
        return result

    @staticmethod
    def _mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ThemeError(f"{label} must be an object with string keys.")
        return value

    @staticmethod
    def _exact_keys(data: dict[str, Any], expected: frozenset[str], label: str) -> None:
        missing = sorted(expected - set(data))
        unexpected = sorted(set(data) - expected)
        if missing:
            raise ThemeError(f"{label} is missing keys: {', '.join(missing)}.")
        if unexpected:
            raise ThemeError(f"{label} contains unknown keys: {', '.join(unexpected)}.")

    @staticmethod
    def _string(value: object, label: str) -> str:
        if not isinstance(value, str):
            raise ThemeError(f"{label} must be a string.")
        return value


class ThemeManagedThemeVerifier:
    """Verify exact managed layout, receipt, manifest bytes, and identity."""

    def __init__(
        self,
        receipt_reader: ThemeInstallationReceiptReader | None = None,
        manifest_reader: ThemeManifestReader | None = None,
    ) -> None:
        self._receipt_reader = receipt_reader or ThemeInstallationReceiptReader()
        self._manifest_reader = manifest_reader or ThemeManifestReader()

    def verify_directory(
        self,
        directory: Path,
        container_root: Path,
        state: ThemeManagedState,
        *,
        root_id: str = "project",
    ) -> ThemeManagedRecord:
        if directory.is_symlink() or not directory.is_dir():
            raise ThemeError("Managed theme version path must be a regular directory.")
        resolved_container = container_root.resolve()
        resolved_directory = directory.resolve()
        if not resolved_directory.is_relative_to(resolved_container):
            raise ThemeError("Managed theme directory escapes its approved container.")
        relative_directory = resolved_directory.relative_to(resolved_container)
        if len(relative_directory.parts) != 2:
            raise ThemeError("Managed theme path must be exactly <theme-id>/<version>.")

        try:
            entries = tuple(sorted(directory.iterdir(), key=lambda item: item.name))
        except OSError as exc:
            raise ThemeError("Managed theme directory could not be inspected.") from exc
        if any(item.is_symlink() for item in entries):
            raise ThemeError("Managed theme files must not be symlinks.")
        names = {item.name for item in entries}
        expected_names = {THEME_MANIFEST_NAME, THEME_INSTALLATION_RECEIPT_NAME}
        if THEME_MANIFEST_NAME not in names:
            raise ThemeError(f"Managed theme is missing {THEME_MANIFEST_NAME}.")
        if THEME_INSTALLATION_RECEIPT_NAME not in names:
            raise ThemeError(
                f"Managed theme is missing {THEME_INSTALLATION_RECEIPT_NAME}."
            )
        if names != expected_names or not all(item.is_file() for item in entries):
            raise ThemeError(
                "Managed theme directory must contain only its manifest and receipt."
            )

        manifest_path = directory / THEME_MANIFEST_NAME
        try:
            with manifest_path.open("rb") as stream:
                manifest_content = stream.read(MAX_THEME_MANIFEST_BYTES + 1)
        except OSError as exc:
            raise ThemeError("Managed theme manifest could not be read.") from exc
        if len(manifest_content) > MAX_THEME_MANIFEST_BYTES:
            raise ThemeError("Managed theme manifest exceeds the size limit.")
        receipt = self._receipt_reader.read(directory / THEME_INSTALLATION_RECEIPT_NAME)
        if len(manifest_content) != receipt.manifest_size:
            raise ThemeError("Managed theme manifest size does not match its receipt.")
        if hashlib.sha256(manifest_content).hexdigest() != receipt.manifest_sha256:
            raise ThemeError("Managed theme manifest SHA-256 does not match its receipt.")
        try:
            manifest_text = manifest_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ThemeError("Managed theme manifest must be UTF-8 text.") from exc
        manifest = self._manifest_reader.read_text(manifest_text)
        if (
            manifest.metadata.theme_id != receipt.theme_id
            or manifest.metadata.version != receipt.version
        ):
            raise ThemeError("Managed theme manifest identity does not match its receipt.")
        if relative_directory.parts != (
            receipt.theme_id.value,
            receipt.version.value,
        ):
            raise ThemeError("Managed theme directory identity does not match its receipt.")
        prefix = (
            THEME_MANAGED_DIRECTORY
            if state == ThemeManagedState.ACTIVE
            else THEME_DISABLED_DIRECTORY
        )
        return ThemeManagedRecord(
            state,
            f"{prefix}/{receipt.theme_id.value}/{receipt.version.value}",
            manifest,
            receipt,
            root_id,
        )


__all__ = [
    "MAX_THEME_RECEIPT_BYTES",
    "THEME_DISABLED_DIRECTORY",
    "THEME_INSTALLATION_RECEIPT_NAME",
    "THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION",
    "THEME_MANAGED_DIRECTORY",
    "THEME_TRUST_POLICY_ID",
    "ThemeInstallationReceipt",
    "ThemeInstallationReceiptReader",
    "ThemeManagedIssue",
    "ThemeManagedRecord",
    "ThemeManagedState",
    "ThemeManagedThemeVerifier",
    "ThemeManagedVerificationReport",
    "validate_theme_sha256",
    "validate_theme_source_label",
]
