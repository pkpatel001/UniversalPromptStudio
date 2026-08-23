"""Replaceable module-loading boundary for explicitly trusted local plugins."""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Protocol

from Engineering.core.exceptions import PluginError

from .models import PluginEntryPoint
from .runtime_api import RuntimePlugin
from .runtime_snapshot import PluginDirectorySnapshot, PluginSnapshotFile


@dataclass(frozen=True, slots=True)
class LoadedPlugin:
    """One instantiated plugin plus its private import namespace."""

    namespace: str
    instance: RuntimePlugin
    finder: importlib.abc.MetaPathFinder


class PluginModuleLoader(Protocol):
    """Boundary that can later be replaced by a process-isolated loader."""

    def load(
        self,
        snapshot: PluginDirectorySnapshot,
        entry_point: PluginEntryPoint,
        namespace: str,
    ) -> LoadedPlugin:
        """Load and instantiate an entry point from approved snapshot bytes."""

    def unload(self, loaded: LoadedPlugin) -> None:
        """Remove loader-owned import state."""


class _SnapshotSourceLoader(importlib.abc.Loader):
    def __init__(self, source: PluginSnapshotFile, is_package: bool) -> None:
        self._source = source
        self._is_package = is_package

    def create_module(self, spec: object) -> ModuleType | None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        try:
            source = self._source.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PluginError(
                f"Plugin Python source is not UTF-8: {self._source.relative_path}."
            ) from exc
        code = compile(source, self._source.relative_path, "exec")
        exec(code, module.__dict__)


class _SnapshotFinder(importlib.abc.MetaPathFinder):
    def __init__(self, namespace: str, snapshot: PluginDirectorySnapshot) -> None:
        self._namespace = namespace
        self._files = {item.relative_path: item for item in snapshot.files}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        prefix = f"{self._namespace}."
        if not fullname.startswith(prefix):
            return None
        relative_module = fullname[len(prefix) :].replace(".", "/")
        module_source = self._files.get(f"{relative_module}.py")
        package_source = self._files.get(f"{relative_module}/__init__.py")
        source = module_source or package_source
        if source is None:
            directory_prefix = f"{relative_module}/"
            if any(path.startswith(directory_prefix) for path in self._files):
                spec = ModuleSpec(fullname, loader=None, is_package=True)
                spec.submodule_search_locations = []
                return spec
            return None
        is_package = package_source is not None and module_source is None
        loader = _SnapshotSourceLoader(source, is_package)
        return importlib.util.spec_from_loader(fullname, loader, is_package=is_package)


class TrustedInProcessLoader:
    """Load approved snapshot bytes with the host process's full authority.

    This loader is intentionally not a sandbox. It avoids persistent ``sys.path``
    changes and gives each plugin a private module namespace, but plugin code has
    the same operating-system and Python authority as the host process.
    """

    def load(
        self,
        snapshot: PluginDirectorySnapshot,
        entry_point: PluginEntryPoint,
        namespace: str,
    ) -> LoadedPlugin:
        module_name, _, class_name = entry_point.value.partition(":")
        if not module_name or not class_name:
            raise PluginError("Plugin runtime entry point is invalid.")
        if namespace in sys.modules:
            raise PluginError("Plugin runtime namespace is already loaded.")

        finder = _SnapshotFinder(namespace, snapshot)
        root_package = ModuleType(namespace)
        root_package.__package__ = namespace
        root_package.__path__ = []
        root_package.__spec__ = importlib.util.spec_from_loader(
            namespace, loader=None, is_package=True
        )
        sys.modules[namespace] = root_package
        sys.meta_path.insert(0, finder)
        try:
            full_module_name = f"{namespace}.{module_name}"
            module = importlib.import_module(full_module_name)
            entry_type = getattr(module, class_name, None)
            if not isinstance(entry_type, type):
                raise PluginError(f"Plugin entry-point class was not found: {entry_point.value}.")
            instance = entry_type()
            if not isinstance(instance, RuntimePlugin):
                raise PluginError(
                    "Plugin entry point must implement activate(context) and "
                    "deactivate(context)."
                )
            return LoadedPlugin(namespace, instance, finder)
        except Exception:
            self._remove(namespace, finder)
            raise

    def unload(self, loaded: LoadedPlugin) -> None:
        self._remove(loaded.namespace, loaded.finder)

    @staticmethod
    def _remove(namespace: str, finder: importlib.abc.MetaPathFinder) -> None:
        sys.meta_path[:] = [item for item in sys.meta_path if item is not finder]
        prefix = f"{namespace}."
        for name in tuple(sys.modules):
            if name == namespace or name.startswith(prefix):
                sys.modules.pop(name, None)


__all__ = ["LoadedPlugin", "PluginModuleLoader", "TrustedInProcessLoader"]
