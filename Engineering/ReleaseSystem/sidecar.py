"""Validation and staging for the frozen desktop sidecar artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from Engineering.core.exceptions import ReleaseError
from Engineering.core.filesystem import ensure_directory
from Engineering.core.version import VERSION

from .models import PackageFormat

SIDECAR_BASENAME = "universal-prompt-studio-backend"
SIDECAR_IDENTITY = "com.universalpromptstudio.backend"


class SidecarPackageBuilder:
    """Verify and stage exactly one target-triple frozen sidecar."""

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Validate the generated manifest and copy its executable to staging."""

        if PackageFormat.DESKTOP_SIDECAR not in formats:
            return ()
        binary_root = project_root / "Frontend" / "src-tauri" / "binaries"
        binaries = tuple(sorted(binary_root.glob(f"{SIDECAR_BASENAME}-*.exe")))
        manifests = tuple(sorted(binary_root.glob(f"{SIDECAR_BASENAME}-*.manifest.json")))
        if len(binaries) != 1 or len(manifests) != 1:
            raise ReleaseError("Exactly one built sidecar and checksum manifest are required.")

        binary = binaries[0]
        manifest_path = manifests[0]
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            artifact = manifest["artifact"]
            builder = manifest["builder"]
            if not isinstance(artifact, dict) or not isinstance(builder, dict):
                raise TypeError("artifact and builder mappings are required")
            expected_lock = hashlib.sha256(
                (project_root / "Scripts" / "sidecar-requirements.lock").read_bytes()
            ).hexdigest()
            actual_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
            valid = (
                manifest.get("schema_version") == 1
                and manifest.get("sidecar_identity") == SIDECAR_IDENTITY
                and manifest.get("application_version") == VERSION
                and manifest.get("protocol_version") == 1
                and isinstance(manifest.get("target_triple"), str)
                and bool(manifest["target_triple"])
                and builder.get("pyinstaller") == "6.22.2"
                and builder.get("lock_sha256") == expected_lock
                and artifact.get("file_name") == binary.name
                and artifact.get("size") == binary.stat().st_size
                and artifact.get("sha256") == actual_hash
            )
        except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
            raise ReleaseError(f"Cannot validate sidecar build manifest: {exc}") from exc
        if not valid:
            raise ReleaseError("Sidecar build manifest does not match the executable.")

        ensure_directory(output_directory)
        target = output_directory / binary.name
        shutil.copy2(binary, target)
        return (target,)
