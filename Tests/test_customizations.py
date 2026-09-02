"""A-006 managed theme and trusted-extension lifecycle integration tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from Backend.application.customizations import ManagedCustomizationService
from Backend.core.container import create_sqlite_container
from Backend.infrastructure.repositories.sqlite import DATABASE_FILE_NAME
from Backend.ipc.customization_routes import (
    CUSTOMIZATION_CATALOG_COMMAND,
    EXTENSION_ACTIVATE_COMMAND,
    THEME_LIFECYCLE_COMMAND,
)
from Backend.ipc.models import IPC_PROTOCOL_VERSION
from Backend.ipc.protocol import parse_request
from Backend.ipc.router import ApplicationIpcRouter
from Engineering.Tests.test_plugin_runtime import _write_plugin
from Engineering.Tests.test_theme_installation import _package
from Engineering.ThemeSystem import ThemePackageInspector


def _request(command: str, payload: dict[str, object]) -> bytes:
    import json

    return json.dumps(
        {
            "schema_version": IPC_PROTOCOL_VERSION,
            "request_id": "a006-test",
            "command": command,
            "payload": payload,
        }
    ).encode("utf-8")


def test_empty_catalog_declares_exact_supported_trust_boundaries(tmp_path: Path) -> None:
    catalog = ManagedCustomizationService(tmp_path).catalog()

    assert catalog == {
        "schema_version": 1,
        "boundaries": {
            "theme_install": "managed-inbox-only",
            "theme_remove": "unsupported",
            "extension_install": "unsupported",
            "extension_remove": "unsupported",
            "extension_runtime": "explicit-session-full-trust",
            "remote_discovery": "unsupported",
        },
        "theme_selections": [],
        "themes": [],
        "theme_packages": [],
        "extensions": [],
        "issues": [],
    }
    assert (tmp_path / "themes").is_dir()
    assert (tmp_path / "theme-packages").is_dir()
    assert (tmp_path / "extensions").is_dir()


def test_theme_install_disable_restore_is_exact_reversible_and_not_silent(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    staged = _package(tmp_path, theme_id="example.desktop")
    inbox_package = tmp_path / "theme-packages" / staged.name
    shutil.move(staged, inbox_package)
    digest = ThemePackageInspector().inspect(inbox_package).sha256

    before = service.catalog()
    installed = service.install_theme(
        inbox_package.name,
        digest,
        acknowledge_external_theme=True,
    )
    active = service.catalog()
    disabled = service.change_theme_state(
        "example.desktop",
        "1.0.0",
        "disable",
        digest,
        acknowledge_lifecycle_change=True,
    )
    inactive = service.catalog()
    restored = service.change_theme_state(
        "example.desktop",
        "1.0.0",
        "restore",
        digest,
        acknowledge_lifecycle_change=True,
    )

    assert before["theme_selections"] == []
    assert installed["applied"] is True and installed["state"] == "active"
    assert active["themes"][0]["trust_state"] == "verified-exact-package-sha256"
    assert active["theme_selections"][0]["theme_id"] == "example.desktop"
    assert disabled["applied"] is True and disabled["state"] == "disabled"
    assert inactive["theme_selections"] == []
    assert inactive["themes"][0]["state"] == "disabled"
    assert restored["applied"] is True and restored["state"] == "active"


def test_theme_install_requires_exact_hash_and_external_acknowledgement(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    staged = _package(tmp_path, theme_id="example.blocked")
    inbox_package = tmp_path / "theme-packages" / staged.name
    shutil.move(staged, inbox_package)
    digest = ThemePackageInspector().inspect(inbox_package).sha256

    unacknowledged = service.install_theme(
        inbox_package.name,
        digest,
        acknowledge_external_theme=False,
    )

    assert unacknowledged["applied"] is False
    assert unacknowledged["issues"][0]["code"] == "theme.trust.acknowledgement-required"
    assert not (tmp_path / "themes" / "Installed").exists()


def test_extension_activation_is_digest_approved_permission_free_and_session_only(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    _write_plugin(
        tmp_path / "extensions",
        """
class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", "ready")

    def deactivate(self, context):
        return None
""",
    )
    extension = service.catalog()["extensions"][0]

    active = service.activate_extension(
        extension["plugin_id"],
        extension["version"],
        extension["directory_sha256"],
        acknowledge_full_trust=True,
    )
    restarted_view = ManagedCustomizationService(tmp_path).catalog()["extensions"][0]
    inactive = service.deactivate_extension(
        extension["plugin_id"],
        extension["version"],
        extension["directory_sha256"],
    )

    assert extension["trust_state"] == "full-trust-required"
    assert active["runtime_state"] == "active"
    assert active["contribution_count"] == 1
    assert restarted_view["runtime_state"] == "inactive"
    assert restarted_view["restart_behavior"] == "inactive-after-restart"
    assert inactive["runtime_state"] == "inactive"


def test_permission_request_is_visible_and_blocked_before_digest_or_execution(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    _write_plugin(
        tmp_path / "extensions",
        "class EchoPlugin:\n    pass\n",
        permissions=("network.read",),
    )

    extension = service.catalog()["extensions"][0]

    assert extension["permissions"] == ["network.read"]
    assert extension["trust_state"] == "permission-request-blocked"
    assert extension["directory_sha256"] is None


def test_ipc_routes_reject_paths_and_require_explicit_confirmations(tmp_path: Path) -> None:
    router = ApplicationIpcRouter(lambda: create_sqlite_container(tmp_path / DATABASE_FILE_NAME))
    catalog = router.handle(parse_request(_request(CUSTOMIZATION_CATALOG_COMMAND, {})))
    traversal = router.handle(
        parse_request(
            _request(
                THEME_LIFECYCLE_COMMAND,
                {
                    "theme_id": "../escape",
                    "version": "1.0.0",
                    "action": "disable",
                    "approved_package_sha256": "a" * 64,
                    "acknowledge_lifecycle_change": True,
                    "confirm": True,
                },
            )
        )
    )
    unconfirmed = router.handle(
        parse_request(
            _request(
                EXTENSION_ACTIVATE_COMMAND,
                {
                    "plugin_id": "example.echo",
                    "version": "1.0.0",
                    "directory_sha256": "a" * 64,
                    "acknowledge_full_trust": True,
                    "confirm": False,
                },
            )
        )
    )

    assert catalog.error is None
    assert catalog.result["boundaries"]["remote_discovery"] == "unsupported"
    assert traversal.error is not None and traversal.error.code.value == "ipc.invalid_payload"
    assert unconfirmed.error is not None and unconfirmed.error.code.value == "ipc.invalid_payload"


def test_external_theme_cannot_claim_the_reserved_builtin_namespace(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    staged = _package(tmp_path, theme_id="ups.mimic")
    inbox_package = tmp_path / "theme-packages" / staged.name
    shutil.move(staged, inbox_package)
    digest = ThemePackageInspector().inspect(inbox_package).sha256

    result = service.install_theme(
        inbox_package.name,
        digest,
        acknowledge_external_theme=True,
    )

    assert result["applied"] is False
    assert result["issues"][0]["code"] == "theme.identity.reserved"
    assert not (tmp_path / "themes" / "Installed").exists()


def test_any_managed_theme_integrity_issue_withholds_the_dynamic_catalog(
    tmp_path: Path,
) -> None:
    service = ManagedCustomizationService(tmp_path)
    staged = _package(tmp_path, theme_id="example.integrity")
    inbox_package = tmp_path / "theme-packages" / staged.name
    shutil.move(staged, inbox_package)
    digest = ThemePackageInspector().inspect(inbox_package).sha256
    installed = service.install_theme(
        inbox_package.name,
        digest,
        acknowledge_external_theme=True,
    )
    assert installed["applied"] is True
    manifest = (
        tmp_path / "themes" / "Installed" / "example.integrity" / "1.0.0" / "theme-manifest.yaml"
    )
    manifest.write_bytes(manifest.read_bytes().replace(b"#276A73", b"#336699"))

    catalog = service.catalog()

    assert catalog["theme_selections"] == []
    assert catalog["issues"][0]["code"] == "theme.managed.integrity-invalid"
