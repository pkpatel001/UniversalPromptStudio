"""E-013.5 approval-gated trusted runtime and lifecycle tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import PluginError
from Engineering.PluginSystem import (
    PLUGIN_MANIFEST_NAME,
    PluginDirectorySnapshotter,
    PluginDiscoveryRoot,
    PluginLifecycleState,
    PluginRuntimeApproval,
    PluginRuntimeEvent,
    PluginRuntimeManager,
)


def _write_plugin(
    root: Path,
    source: str,
    *,
    plugin_id: str = "example.echo",
    directory: str = "echo",
    entry_point: str = "plugin:EchoPlugin",
    permissions: tuple[str, ...] = (),
    dependencies: tuple[tuple[str, str], ...] = (),
    extra: tuple[tuple[str, str], ...] = (),
) -> Path:
    plugin_root = root / directory
    plugin_root.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": "Echo Plugin",
            "version": "1.0.0",
            "sdk_version": 1,
            "description": "Trusted runtime fixture.",
            "entry_point": entry_point,
            "capabilities": ["commands"],
            "permissions": list(permissions),
            "dependencies": [
                {"id": dependency_id, "version": version} for dependency_id, version in dependencies
            ],
        },
    }
    (plugin_root / PLUGIN_MANIFEST_NAME).write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    module_name = entry_point.partition(":")[0]
    module_path = plugin_root / f"{module_name.replace('.', '/')}.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(source, encoding="utf-8")
    for relative_path, content in extra:
        path = plugin_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return plugin_root


def _approval(
    manager: PluginRuntimeManager,
    root: Path,
    *,
    plugin_id: str = "example.echo",
    digest: str | None = None,
    acknowledge: bool = True,
) -> PluginRuntimeApproval:
    status = manager.digest(PluginDiscoveryRoot("project", root), plugin_id)
    return PluginRuntimeApproval(
        status.plugin_id,
        status.version,
        status.root_id,
        digest or status.directory_sha256,
        acknowledge,
    )


class _Events:
    def __init__(self) -> None:
        self.items: list[PluginRuntimeEvent] = []

    def publish(self, event: PluginRuntimeEvent) -> None:
        self.items.append(event)


def test_snapshot_digest_is_exact_bounded_and_rejects_symlinks(tmp_path: Path) -> None:
    plugin_root = _write_plugin(tmp_path, "class EchoPlugin:\n    pass\n")
    snapshotter = PluginDirectorySnapshotter()
    first = snapshotter.capture(plugin_root)
    second = snapshotter.capture(plugin_root)
    (plugin_root / "plugin.py").write_text(
        "class EchoPlugin:\n    changed = True\n", encoding="utf-8"
    )

    assert first.sha256 == second.sha256
    assert snapshotter.capture(plugin_root).sha256 != first.sha256
    (plugin_root / "__pycache__").mkdir()
    with pytest.raises(PluginError, match="excluded content"):
        snapshotter.capture(plugin_root)
    (plugin_root / "__pycache__").rmdir()
    try:
        (plugin_root / "linked.py").symlink_to(plugin_root / "plugin.py")
    except OSError:
        pytest.skip("Symlink creation is unavailable on this Windows host.")
    with pytest.raises(PluginError, match="symlinks"):
        snapshotter.capture(plugin_root)


def test_activation_commits_then_deactivation_cleans_everything(tmp_path: Path) -> None:
    source = """
from .helper import VALUE

class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", VALUE)

    def deactivate(self, context):
        return None
"""
    _write_plugin(tmp_path, source, extra=(("helper.py", "VALUE = 'ready'\n"),))
    events = _Events()
    manager = PluginRuntimeManager(events=events)
    approval = _approval(manager, tmp_path)

    active = manager.activate(
        PluginDiscoveryRoot("project", tmp_path),
        "example.echo",
        "1.0.0",
        approval,
    )

    namespace = f"_ups_plugin_{active.directory_sha256[:24]}"
    assert active.state == PluginLifecycleState.ACTIVE
    assert active.contributions[0].value == "ready"
    assert namespace in sys.modules
    assert [event.name for event in events.items] == ["PluginLoaded"]

    inactive = manager.deactivate("project", "example.echo", "1.0.0")

    assert inactive.state == PluginLifecycleState.INACTIVE
    assert inactive.contributions == ()
    assert not any(name == namespace or name.startswith(f"{namespace}.") for name in sys.modules)
    assert [event.name for event in events.items] == [
        "PluginLoaded",
        "PluginUnloaded",
    ]


def test_dotted_entry_point_uses_snapshot_namespace_packages(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        """
from .helper import VALUE

class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", VALUE)

    def deactivate(self, context):
        return None
""",
        entry_point="echo_plugin.main:EchoPlugin",
        extra=(("echo_plugin/helper.py", "VALUE = 'nested'\n"),),
    )
    manager = PluginRuntimeManager()

    active = manager.activate(
        PluginDiscoveryRoot("project", tmp_path),
        "example.echo",
        "1.0.0",
        _approval(manager, tmp_path),
    )

    assert active.state == PluginLifecycleState.ACTIVE
    assert active.contributions[0].value == "nested"
    assert (
        manager.deactivate("project", "example.echo", "1.0.0").state
        == PluginLifecycleState.INACTIVE
    )


def test_runtime_dependency_must_be_active_before_consumer(tmp_path: Path) -> None:
    source = """
class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", object())

    def deactivate(self, context):
        return None
"""
    _write_plugin(
        tmp_path,
        source,
        plugin_id="example.base",
        directory="base",
    )
    _write_plugin(
        tmp_path,
        source,
        plugin_id="example.consumer",
        directory="consumer",
        dependencies=(("example.base", ">=1,<2"),),
    )
    manager = PluginRuntimeManager()
    root = PluginDiscoveryRoot("project", tmp_path)
    consumer_approval = _approval(manager, tmp_path, plugin_id="example.consumer")

    with pytest.raises(PluginError, match="dependency is not active"):
        manager.activate(
            root,
            "example.consumer",
            "1.0.0",
            consumer_approval,
        )

    base = manager.activate(
        root,
        "example.base",
        "1.0.0",
        _approval(manager, tmp_path, plugin_id="example.base"),
    )
    consumer = manager.activate(
        root,
        "example.consumer",
        "1.0.0",
        consumer_approval,
    )

    assert base.state == PluginLifecycleState.ACTIVE
    assert consumer.state == PluginLifecycleState.ACTIVE
    assert (
        manager.deactivate("project", "example.consumer", "1.0.0").state
        == PluginLifecycleState.INACTIVE
    )
    assert (
        manager.deactivate("project", "example.base", "1.0.0").state
        == PluginLifecycleState.INACTIVE
    )


def test_approval_and_permission_policy_block_before_code_runs(tmp_path: Path) -> None:
    marker = tmp_path / "executed.txt"
    _write_plugin(
        tmp_path,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
    )
    manager = PluginRuntimeManager()
    root = PluginDiscoveryRoot("project", tmp_path)

    with pytest.raises(PluginError, match="full-trust"):
        manager.activate(
            root,
            "example.echo",
            "1.0.0",
            _approval(manager, tmp_path, acknowledge=False),
        )
    with pytest.raises(PluginError, match="does not match"):
        manager.activate(
            root,
            "example.echo",
            "1.0.0",
            _approval(manager, tmp_path, digest="0" * 64),
        )
    assert not marker.exists()

    permission_root = tmp_path / "permission-root"
    _write_plugin(
        permission_root,
        "class EchoPlugin:\n    pass\n",
        permissions=("network.read",),
    )
    with pytest.raises(PluginError, match="permission enforcement"):
        manager.digest(PluginDiscoveryRoot("permission", permission_root), "example.echo")


def test_activation_failure_rolls_back_contributions_and_modules(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        """
class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", object())
        raise RuntimeError("activation failed")

    def deactivate(self, context):
        return None
""",
    )
    events = _Events()
    manager = PluginRuntimeManager(events=events)
    approval = _approval(manager, tmp_path)

    result = manager.activate(
        PluginDiscoveryRoot("project", tmp_path),
        "example.echo",
        "1.0.0",
        approval,
    )

    namespace = f"_ups_plugin_{result.directory_sha256[:24]}"
    assert result.state == PluginLifecycleState.FAILED
    assert result.contributions == ()
    assert "activation failed" in (result.error or "")
    assert not any(name.startswith(namespace) for name in sys.modules)
    assert events.items == []


def test_undeclared_capability_is_transactional_failure(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        """
class EchoPlugin:
    def activate(self, context):
        context.register("views", "echo", object())

    def deactivate(self, context):
        return None
""",
    )
    manager = PluginRuntimeManager()

    result = manager.activate(
        PluginDiscoveryRoot("project", tmp_path),
        "example.echo",
        "1.0.0",
        _approval(manager, tmp_path),
    )

    assert result.state == PluginLifecycleState.FAILED
    assert "did not declare capability" in (result.error or "")
    assert manager.registry.contributions() == ()


def test_deactivation_failure_still_cleans_host_state(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        """
class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", object())

    def deactivate(self, context):
        raise RuntimeError("shutdown failed")
""",
    )
    events = _Events()
    manager = PluginRuntimeManager(events=events)
    active = manager.activate(
        PluginDiscoveryRoot("project", tmp_path),
        "example.echo",
        "1.0.0",
        _approval(manager, tmp_path),
    )

    failed = manager.deactivate("project", "example.echo", "1.0.0")

    assert active.state == PluginLifecycleState.ACTIVE
    assert failed.state == PluginLifecycleState.FAILED
    assert failed.contributions == ()
    assert [event.name for event in events.items] == ["PluginLoaded"]


def test_runtime_cli_digest_and_one_shot_probe(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path,
        """
class EchoPlugin:
    def activate(self, context):
        context.register("commands", "echo", "ready")

    def deactivate(self, context):
        return None
""",
    )
    runner = CliRunner()
    digest_result = runner.invoke(
        app,
        ["plugin", "runtime", "digest", "example.echo", "--root", str(tmp_path)],
        terminal_width=200,
    )
    digest = next(
        line.partition(": ")[2]
        for line in digest_result.output.splitlines()
        if line.startswith("Directory SHA-256:")
    )
    probe = runner.invoke(
        app,
        [
            "plugin",
            "runtime",
            "probe",
            "example.echo",
            "--root",
            str(tmp_path),
            "--approve-sha256",
            digest,
            "--acknowledge-full-trust",
        ],
        terminal_width=200,
    )

    assert digest_result.exit_code == 0
    assert "Plugin code imported: no" in digest_result.output
    assert probe.exit_code == 0, probe.output
    assert "Runtime activation: active contributions=1" in probe.output
    assert "Runtime deactivation: inactive" in probe.output
    assert "Trust persistence: none" in probe.output
