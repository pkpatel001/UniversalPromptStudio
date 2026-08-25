"""Contract tests for the locked A-001.2 sidecar build inputs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Backend.ipc import IPC_PROTOCOL_VERSION, SIDECAR_IDENTITY
from Engineering.core.version import VERSION
from Scripts.ups_sidecar import main

ROOT = Path(__file__).resolve().parents[1]


def test_sidecar_identity_probe_is_exact(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--identity"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "application_version": VERSION,
        "protocol_version": IPC_PROTOCOL_VERSION,
        "sidecar_identity": SIDECAR_IDENTITY,
    }


def test_sidecar_rejects_all_runtime_arguments() -> None:
    assert main(["--unknown"]) == 64


def test_build_toolchain_is_hash_locked() -> None:
    lines = [
        line
        for line in (ROOT / "Scripts" / "sidecar-requirements.lock")
        .read_text(encoding="utf-8")
        .splitlines()
        if line and not line.startswith("#")
    ]
    requirements = [line for line in lines if not line.startswith(" ")]
    hashes = [line.strip() for line in lines if line.startswith(" ")]
    assert len(requirements) == 13
    assert all("==" in line and line.endswith("\\") for line in requirements)
    assert len(hashes) == len(requirements)
    assert all(line.startswith("--hash=sha256:") and len(line) == 78 for line in hashes)


def test_tauri_declares_target_triple_sidecar_base_name() -> None:
    config = json.loads(
        (ROOT / "Frontend" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    assert config["bundle"]["externalBin"] == ["binaries/universal-prompt-studio-backend"]
    assert config["bundle"]["resources"] == ["binaries/*.manifest.json"]
