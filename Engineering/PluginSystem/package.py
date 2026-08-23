"""Read-only E-013.4 plugin package inspection without archive extraction."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from Engineering.core.exceptions import PluginError

from .manifest import PLUGIN_MANIFEST_NAME, PluginManifestReader
from .models import PluginManifest

PLUGIN_PACKAGE_SUFFIX = ".ups-plugin.zip"
MAX_PLUGIN_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_PLUGIN_PACKAGE_ENTRIES = 1024
MAX_PLUGIN_MEMBER_BYTES = 16 * 1024 * 1024
MAX_PLUGIN_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_PLUGIN_COMPRESSION_RATIO = 200
_MAX_MANIFEST_BYTES = 256 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PORTABLE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
_ALLOWED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
_FORBIDDEN_SEGMENTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "credentials",
        "node_modules",
        "secrets",
    }
)
_SECRET_SUFFIXES = (".key", ".p12", ".pem", ".pfx")
_WINDOWS_RESERVED = frozenset(
    {"aux", "con", "nul", "prn"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)


@dataclass(frozen=True, slots=True)
class PluginPackageEntry:
    """One regular file in a validated plugin package."""

    relative_path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PluginPackage:
    """Immutable metadata for an inspected canonical plugin ZIP."""

    filename: str
    size: int
    sha256: str
    manifest: PluginManifest
    entries: tuple[PluginPackageEntry, ...]

    @property
    def plugin_id(self) -> str:
        return self.manifest.metadata.plugin_id.value

    @property
    def version(self) -> str:
        return self.manifest.metadata.version.value


class PluginTrustStatus(Enum):
    """Ephemeral exact-byte approval status; never a code-safety claim."""

    UNAPPROVED = "unapproved"
    HASH_MISMATCH = "hash-mismatch"
    HASH_APPROVED = "hash-approved"


@dataclass(frozen=True, slots=True)
class PluginTrustAssessment:
    """Result of comparing a package with an explicit SHA-256 approval."""

    status: PluginTrustStatus
    package_sha256: str
    approved_sha256: str | None = None

    @property
    def approved(self) -> bool:
        return self.status == PluginTrustStatus.HASH_APPROVED


class PluginTrustPolicy:
    """Assess only an explicit in-memory hash pin; persist no trust state."""

    def assess(
        self,
        package: PluginPackage,
        approved_sha256: str | None,
    ) -> PluginTrustAssessment:
        if approved_sha256 is None:
            return PluginTrustAssessment(
                PluginTrustStatus.UNAPPROVED,
                package.sha256,
            )
        if not _SHA256.fullmatch(approved_sha256):
            raise PluginError(
                "Approved plugin package SHA-256 must be 64 lowercase hexadecimal characters."
            )
        status = (
            PluginTrustStatus.HASH_APPROVED
            if approved_sha256 == package.sha256
            else PluginTrustStatus.HASH_MISMATCH
        )
        return PluginTrustAssessment(status, package.sha256, approved_sha256)


class PluginPackageInspector:
    """Validate a canonical plugin ZIP without extracting or importing it."""

    def __init__(self, reader: PluginManifestReader | None = None) -> None:
        self._reader = reader or PluginManifestReader()

    def inspect(self, path: Path) -> PluginPackage:
        """Read bounded archive metadata and hash every regular member."""

        if path.is_symlink():
            raise PluginError("Plugin package must not be a symlink.")
        if not path.is_file():
            raise PluginError(f"Plugin package is not a regular file: {path.name}")
        if not path.name.endswith(PLUGIN_PACKAGE_SUFFIX):
            raise PluginError(
                f"Plugin package filename must end with {PLUGIN_PACKAGE_SUFFIX}."
            )

        package_bytes = self._read_package(path)
        size = len(package_bytes)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(package_bytes), mode="r") as archive:
                entries, manifest_text = self._inspect_entries(archive)
        except (OSError, RuntimeError, UnicodeError, zipfile.BadZipFile) as exc:
            raise PluginError(f"Plugin package could not be inspected: {exc}") from exc

        manifest = self._reader.read_text(manifest_text)
        expected_name = (
            f"{manifest.metadata.plugin_id.value}-"
            f"{manifest.metadata.version.value}{PLUGIN_PACKAGE_SUFFIX}"
        )
        if path.name != expected_name:
            raise PluginError(
                f"Plugin package filename must match manifest identity: {expected_name}."
            )
        self._require_entry_point(entries, manifest)
        return PluginPackage(
            filename=path.name,
            size=size,
            sha256=package_sha256,
            manifest=manifest,
            entries=entries,
        )

    def _inspect_entries(
        self, archive: zipfile.ZipFile
    ) -> tuple[tuple[PluginPackageEntry, ...], str]:
        infos = archive.infolist()
        if len(infos) > MAX_PLUGIN_PACKAGE_ENTRIES:
            raise PluginError("Plugin package contains too many archive entries.")

        seen: set[str] = set()
        file_infos: list[zipfile.ZipInfo] = []
        total_size = 0
        for info in infos:
            normalized = self._validate_member(info)
            key = normalized.casefold()
            if key in seen:
                raise PluginError(
                    f"Plugin package contains duplicate member path: {normalized}."
                )
            seen.add(key)
            if info.is_dir():
                continue
            total_size += info.file_size
            if info.file_size > MAX_PLUGIN_MEMBER_BYTES:
                raise PluginError(
                    f"Plugin package member exceeds the size limit: {normalized}."
                )
            if total_size > MAX_PLUGIN_UNCOMPRESSED_BYTES:
                raise PluginError("Plugin package exceeds the uncompressed size limit.")
            if (
                info.file_size > 1024 * 1024
                and info.compress_size > 0
                and info.file_size / info.compress_size > MAX_PLUGIN_COMPRESSION_RATIO
            ):
                raise PluginError(
                    f"Plugin package member has an unsafe compression ratio: {normalized}."
                )
            file_infos.append(info)

        names = {info.filename for info in file_infos}
        if PLUGIN_MANIFEST_NAME not in names:
            raise PluginError(
                f"Plugin package is missing root {PLUGIN_MANIFEST_NAME}."
            )
        manifest_info = next(
            info for info in file_infos if info.filename == PLUGIN_MANIFEST_NAME
        )
        if manifest_info.file_size > _MAX_MANIFEST_BYTES:
            raise PluginError("Plugin package manifest exceeds the size limit.")

        entries: list[PluginPackageEntry] = []
        manifest_text: str | None = None
        for info in sorted(file_infos, key=lambda item: item.filename):
            digest = hashlib.sha256()
            content = bytearray() if info.filename == PLUGIN_MANIFEST_NAME else None
            actual_size = 0
            with archive.open(info, mode="r") as stream:
                while chunk := stream.read(64 * 1024):
                    actual_size += len(chunk)
                    digest.update(chunk)
                    if content is not None:
                        content.extend(chunk)
            if actual_size != info.file_size:
                raise PluginError(
                    f"Plugin package member size does not match metadata: {info.filename}."
                )
            entries.append(
                PluginPackageEntry(info.filename, actual_size, digest.hexdigest())
            )
            if content is not None:
                manifest_text = bytes(content).decode("utf-8")

        assert manifest_text is not None
        return tuple(entries), manifest_text

    @staticmethod
    def _validate_member(info: zipfile.ZipInfo) -> str:
        raw = info.orig_filename
        normalized = raw[:-1] if raw.endswith("/") else raw
        parts = normalized.split("/")
        if (
            not normalized
            or "\\" in raw
            or "\0" in raw
            or raw.startswith("/")
            or ":" in raw
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise PluginError(f"Unsafe plugin package member path: {raw}.")
        lowered = tuple(part.casefold() for part in parts)
        if any(
            not _PORTABLE_SEGMENT.fullmatch(part)
            or part.endswith(".")
            or part.partition(".")[0].casefold() in _WINDOWS_RESERVED
            for part in parts
        ):
            raise PluginError(
                f"Non-portable plugin package member path: {normalized}."
            )
        if any(part in _FORBIDDEN_SEGMENTS or part == ".env" for part in lowered):
            raise PluginError(
                f"Forbidden plugin package member path: {normalized}."
            )
        if lowered[-1].endswith(_SECRET_SUFFIXES):
            raise PluginError(
                f"Secret-bearing plugin package member is not allowed: {normalized}."
            )
        if info.flag_bits & 0x1:
            raise PluginError(
                f"Encrypted plugin package member is not allowed: {normalized}."
            )
        if info.compress_type not in _ALLOWED_COMPRESSION:
            raise PluginError(
                f"Unsupported plugin package compression: {normalized}."
            )
        unix_mode = (info.external_attr >> 16) & 0o170000
        if unix_mode == 0o120000:
            raise PluginError(
                f"Symlinked plugin package member is not allowed: {normalized}."
            )
        return normalized

    @staticmethod
    def _require_entry_point(
        entries: tuple[PluginPackageEntry, ...], manifest: PluginManifest
    ) -> None:
        module = manifest.metadata.entry_point.value.partition(":")[0]
        module_path = module.replace(".", "/")
        candidates = {f"{module_path}.py", f"{module_path}/__init__.py"}
        names = {entry.relative_path for entry in entries}
        if names.isdisjoint(candidates):
            expected = " or ".join(sorted(candidates))
            raise PluginError(
                f"Plugin package is missing entry-point module: {expected}."
            )

    @staticmethod
    def _read_package(path: Path) -> bytes:
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_PLUGIN_PACKAGE_BYTES + 1)
        except OSError as exc:
            raise PluginError(f"Plugin package could not be read: {path.name}") from exc
        if len(content) > MAX_PLUGIN_PACKAGE_BYTES:
            raise PluginError("Plugin package exceeds the maximum archive size.")
        return content


__all__ = [
    "MAX_PLUGIN_COMPRESSION_RATIO",
    "MAX_PLUGIN_MEMBER_BYTES",
    "MAX_PLUGIN_PACKAGE_BYTES",
    "MAX_PLUGIN_PACKAGE_ENTRIES",
    "MAX_PLUGIN_UNCOMPRESSED_BYTES",
    "PLUGIN_PACKAGE_SUFFIX",
    "PluginPackage",
    "PluginPackageEntry",
    "PluginPackageInspector",
    "PluginTrustAssessment",
    "PluginTrustPolicy",
    "PluginTrustStatus",
]
