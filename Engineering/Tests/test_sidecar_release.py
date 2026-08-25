"""A-001.2 sidecar staging, checksum, and PE-inspection tests."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

from Engineering.core.exceptions import ReleaseError
from Engineering.ReleaseSystem import PackageFormat, PackageInspector, SidecarPackageBuilder

SIDECAR_NAME = "universal-prompt-studio-backend-x86_64-pc-windows-msvc.exe"


def _write_sidecar(root: Path) -> tuple[Path, Path]:
    binary_root = root / "Frontend" / "src-tauri" / "binaries"
    binary_root.mkdir(parents=True)
    lock_path = root / "Scripts" / "sidecar-requirements.lock"
    lock_path.parent.mkdir()
    lock_path.write_text("locked\n", encoding="utf-8")

    binary = binary_root / SIDECAR_NAME
    content = bytearray(132)
    content[:2] = b"MZ"
    struct.pack_into("<I", content, 0x3C, 128)
    content[128:132] = b"PE\0\0"
    binary.write_bytes(content)
    manifest = {
        "schema_version": 1,
        "sidecar_identity": "com.universalpromptstudio.backend",
        "application_version": "0.2.0-alpha",
        "protocol_version": 1,
        "target_triple": "x86_64-pc-windows-msvc",
        "builder": {
            "python": "3.12.10",
            "pyinstaller": "6.22.2",
            "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        },
        "artifact": {
            "file_name": binary.name,
            "size": binary.stat().st_size,
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        },
    }
    manifest_path = binary_root / SIDECAR_NAME.replace(".exe", ".manifest.json")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return binary, manifest_path


def test_sidecar_builder_validates_stages_and_inspects_pe(tmp_path: Path) -> None:
    binary, _ = _write_sidecar(tmp_path)
    output = tmp_path / "stage"

    artifacts = SidecarPackageBuilder().build(
        tmp_path,
        output,
        (PackageFormat.DESKTOP_SIDECAR,),
    )
    inspected = PackageInspector().inspect(artifacts[0], output)

    assert artifacts[0].read_bytes() == binary.read_bytes()
    assert inspected.package_format is PackageFormat.DESKTOP_SIDECAR
    assert inspected.sha256 == hashlib.sha256(binary.read_bytes()).hexdigest()


def test_sidecar_builder_rejects_manifest_or_binary_drift(tmp_path: Path) -> None:
    binary, _ = _write_sidecar(tmp_path)
    binary.write_bytes(binary.read_bytes() + b"tampered")

    with pytest.raises(ReleaseError, match="does not match"):
        SidecarPackageBuilder().build(
            tmp_path,
            tmp_path / "stage",
            (PackageFormat.DESKTOP_SIDECAR,),
        )
