"""Bounded immutable directory snapshots for runtime approval and loading."""

from __future__ import annotations

import hashlib
import os
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from Engineering.core.exceptions import PluginError

from .discovery import DEFAULT_IGNORED_PLUGIN_DIRECTORIES

MAX_RUNTIME_FILES = 256
MAX_RUNTIME_FILE_BYTES = 8 * 1024 * 1024
MAX_RUNTIME_TOTAL_BYTES = 32 * 1024 * 1024
_DIGEST_HEADER = b"UPS-PLUGIN-DIRECTORY-SNAPSHOT-V1\0"
_WINDOWS_RESERVED = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


@dataclass(frozen=True, slots=True)
class PluginSnapshotFile:
    """One regular file captured as immutable bytes."""

    relative_path: str
    sha256: str
    content: bytes

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(frozen=True, slots=True)
class PluginDirectorySnapshot:
    """One exact, bounded plugin directory revision."""

    root: Path
    sha256: str
    files: tuple[PluginSnapshotFile, ...]

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)

    def file(self, relative_path: str) -> PluginSnapshotFile | None:
        return next(
            (item for item in self.files if item.relative_path == relative_path),
            None,
        )


class PluginDirectorySnapshotter:
    """Capture safe regular files once for both approval and code loading."""

    def capture(self, root: Path) -> PluginDirectorySnapshot:
        """Return a deterministic snapshot without following symlinks."""

        if root.is_symlink():
            raise PluginError("Plugin runtime directory must not be a symlink.")
        resolved_root = root.resolve()
        if not resolved_root.is_dir():
            raise PluginError("Plugin runtime directory is not a directory.")

        paths: list[Path] = []
        for directory, names, filenames in os.walk(resolved_root, followlinks=False):
            directory_path = Path(directory)
            for name in names:
                candidate = directory_path / name
                if candidate.is_symlink():
                    raise PluginError("Plugin runtime directories must not contain symlinks.")
                if name in DEFAULT_IGNORED_PLUGIN_DIRECTORIES:
                    raise PluginError(
                        f"Plugin runtime directory contains excluded content: {name}."
                    )
            names[:] = sorted(
                name for name in names if name not in DEFAULT_IGNORED_PLUGIN_DIRECTORIES
            )
            for filename in sorted(filenames):
                candidate = directory_path / filename
                if candidate.is_symlink():
                    raise PluginError("Plugin runtime directories must not contain symlinks.")
                if not candidate.is_file():
                    raise PluginError("Plugin runtime snapshots accept regular files only.")
                paths.append(candidate)

        if not paths:
            raise PluginError("Plugin runtime directory contains no files.")
        if len(paths) > MAX_RUNTIME_FILES:
            raise PluginError("Plugin runtime directory contains too many files.")

        files: list[PluginSnapshotFile] = []
        casefold_paths: set[str] = set()
        total = 0
        digest = hashlib.sha256(_DIGEST_HEADER)
        for path in sorted(paths, key=lambda item: item.relative_to(resolved_root).as_posix()):
            relative_path = path.relative_to(resolved_root).as_posix()
            self._validate_relative_path(relative_path)
            normalized_path = relative_path.casefold()
            if normalized_path in casefold_paths:
                raise PluginError(f"Plugin runtime contains a duplicate path: {relative_path}.")
            casefold_paths.add(normalized_path)
            try:
                content = path.read_bytes()
            except OSError as exc:
                raise PluginError(
                    f"Plugin runtime file could not be read: {relative_path}."
                ) from exc
            if path.is_symlink() or not path.resolve().is_relative_to(resolved_root):
                raise PluginError(f"Plugin runtime file changed during capture: {relative_path}.")
            if len(content) > MAX_RUNTIME_FILE_BYTES:
                raise PluginError(f"Plugin runtime file exceeds the size limit: {relative_path}.")
            total += len(content)
            if total > MAX_RUNTIME_TOTAL_BYTES:
                raise PluginError("Plugin runtime directory exceeds the total size limit.")
            encoded_path = relative_path.encode("utf-8")
            digest.update(struct.pack(">I", len(encoded_path)))
            digest.update(encoded_path)
            digest.update(struct.pack(">Q", len(content)))
            digest.update(content)
            files.append(
                PluginSnapshotFile(
                    relative_path,
                    hashlib.sha256(content).hexdigest(),
                    content,
                )
            )
        return PluginDirectorySnapshot(resolved_root, digest.hexdigest(), tuple(files))

    @staticmethod
    def _validate_relative_path(value: str) -> None:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in value
            or ":" in value
            or any(ord(character) < 32 for character in value)
        ):
            raise PluginError(f"Unsafe plugin runtime path: {value!r}.")
        for part in path.parts:
            stem = part.rstrip(" .").split(".", 1)[0].casefold()
            if part != part.rstrip(" .") or stem in _WINDOWS_RESERVED:
                raise PluginError(f"Non-portable plugin runtime path: {value!r}.")


__all__ = [
    "MAX_RUNTIME_FILES",
    "MAX_RUNTIME_FILE_BYTES",
    "MAX_RUNTIME_TOTAL_BYTES",
    "PluginDirectorySnapshot",
    "PluginDirectorySnapshotter",
    "PluginSnapshotFile",
]
