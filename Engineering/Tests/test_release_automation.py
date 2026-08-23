"""E-011.4 desktop packaging automation policy tests."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

_ACTION_SHA_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workflow() -> dict[str, object]:
    path = _project_root() / ".github" / "workflows" / "desktop-package.yml"
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(data, dict)
    return data


def test_desktop_workflow_has_read_only_bounded_triggers() -> None:
    workflow = _workflow()

    assert workflow["permissions"] == {"contents": "read"}
    triggers = workflow["on"]
    assert isinstance(triggers, dict)
    assert set(triggers) == {"workflow_dispatch", "push", "pull_request"}
    push = triggers["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]


def test_desktop_workflow_pins_runner_and_actions() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["desktop-package"]
    assert isinstance(job, dict)
    assert job["runs-on"] == "windows-2025"
    assert job["timeout-minutes"] == "45"
    steps = job["steps"]
    assert isinstance(steps, list)
    actions = [step["uses"] for step in steps if isinstance(step, dict) and "uses" in step]

    assert actions
    assert all(
        isinstance(action, str) and _ACTION_SHA_PATTERN.fullmatch(action)
        for action in actions
    )


def test_desktop_workflow_does_not_publish_or_use_secrets() -> None:
    path = _project_root() / ".github" / "workflows" / "desktop-package.yml"
    content = path.read_text(encoding="utf-8")

    assert "secrets." not in content
    assert "contents: write" not in content
    assert "releaseName" not in content
    assert "tagName" not in content
    assert "release/" in content
    assert "retention-days: 14" in content


def test_desktop_script_runs_locked_validation_and_post_build_verification() -> None:
    path = _project_root() / "Scripts" / "package-desktop.ps1"
    content = path.read_text(encoding="utf-8")

    assert '"clippy", "--locked"' in content
    assert '"ruff", "check", "--no-fix"' in content
    assert '"theme", "sync-frontend"' in content
    assert '"test", "--prefix", "Frontend"' in content
    assert '"release", "verify"' in content
    assert "$LASTEXITCODE -ne 0" in content


def test_rust_toolchain_is_patch_pinned_and_matches_cargo_policy() -> None:
    root = _project_root()
    toolchain = tomllib.loads((root / "rust-toolchain.toml").read_text(encoding="utf-8"))
    cargo = tomllib.loads(
        (root / "Frontend" / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    )
    policy = toolchain["toolchain"]
    package = cargo["package"]

    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", policy["channel"])
    assert policy["profile"] == "minimal"
    assert set(policy["components"]) == {"clippy", "rustfmt"}
    assert policy["channel"].startswith(f"{package['rust-version']}.")
