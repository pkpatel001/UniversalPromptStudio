"""Windows DPAPI-backed credential storage for A-004."""

from __future__ import annotations

import ctypes
import hashlib
import os
import tempfile
from ctypes import wintypes
from pathlib import Path

from Backend.application.provider_settings import MAX_CREDENTIAL_LENGTH, OPENAI_CREDENTIAL_REFERENCE

_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


class WindowsDpapiSecretStore:
    """Encrypt credentials for the current Windows user with DPAPI."""

    def __init__(self, directory: Path) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows credential protection is unavailable.")
        if not directory.is_absolute():
            raise ValueError("Credential directory must be absolute.")
        self._directory = directory

    def set(self, reference: str, secret: str) -> None:
        path = self._path(reference)
        if (
            not isinstance(secret, str)
            or not 8 <= len(secret) <= MAX_CREDENTIAL_LENGTH
            or secret != secret.strip()
        ):
            raise ValueError("Credential value is invalid.")
        protected = _protect(secret.encode("utf-8"))
        self._directory.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".credential-", suffix=".tmp", dir=self._directory
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(protected)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    def get(self, reference: str) -> str | None:
        path = self._path(reference)
        if not path.exists():
            return None
        try:
            protected = path.read_bytes()
            if not protected or len(protected) > 4_096:
                raise RuntimeError("Stored credential is invalid.")
            secret = _unprotect(protected).decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise RuntimeError("Stored credential is unavailable.") from exc
        if not 8 <= len(secret) <= MAX_CREDENTIAL_LENGTH:
            raise RuntimeError("Stored credential is invalid.")
        return secret

    def delete(self, reference: str) -> bool:
        path = self._path(reference)
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise RuntimeError("Stored credential could not be cleared.") from exc
        return True

    def contains(self, reference: str) -> bool:
        return self._path(reference).is_file()

    def _path(self, reference: str) -> Path:
        if reference != OPENAI_CREDENTIAL_REFERENCE:
            raise ValueError("Credential reference is invalid.")
        digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()
        return self._directory / f"{digest}.dpapi"


def _protect(value: bytes) -> bytes:
    source, source_buffer = _blob(value)
    result = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        succeeded = crypt32.CryptProtectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(result),
        )
        if not succeeded:
            raise RuntimeError("Credential protection failed.")
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        del source_buffer
        if result.pbData:
            kernel32.LocalFree(result.pbData)


def _unprotect(value: bytes) -> bytes:
    source, source_buffer = _blob(value)
    result = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        succeeded = crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(result),
        )
        if not succeeded:
            raise RuntimeError("Credential resolution failed.")
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        del source_buffer
        if result.pbData:
            kernel32.LocalFree(result.pbData)


def _blob(value: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(value)
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
    return _DataBlob(len(value), pointer), buffer


__all__ = ["WindowsDpapiSecretStore"]
