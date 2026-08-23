"""Safe schema-1 YAML reader owned by the plugin subsystem."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from Engineering.core.exceptions import EngineeringError, PluginError
from Engineering.core.filesystem import read_yaml

from .models import (
    PluginCapability,
    PluginDependency,
    PluginEntryPoint,
    PluginId,
    PluginManifest,
    PluginMetadata,
    PluginPermission,
    PluginSdkVersion,
    PluginVersion,
)

PLUGIN_MANIFEST_NAME = "plugin-manifest.yaml"
PLUGIN_SCHEMA_VERSION = 1
PLUGIN_SDK_API_LEVEL = 1

_ROOT_KEYS = frozenset({"schema_version", "plugin"})
_PLUGIN_KEYS = frozenset(
    {
        "id",
        "name",
        "version",
        "sdk_version",
        "description",
        "entry_point",
        "capabilities",
        "permissions",
        "dependencies",
    }
)
_DEPENDENCY_KEYS = frozenset({"id", "version"})
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class PluginManifestReader:
    """Parse and validate plugin metadata without importing plugin code."""

    def detect_schema_version(self, path: Path) -> int:
        """Read only the schema envelope for E-012 compatibility checks."""

        data = self._read(path)
        value = data.get("schema_version")
        if type(value) is not int:
            raise PluginError("Plugin manifest schema_version must be an integer.")
        return value

    def read(self, path: Path) -> PluginManifest:
        """Read a complete canonical plugin manifest."""

        data = self._read(path)
        self._reject_secret_keys(data)
        self._require_exact_keys(data, _ROOT_KEYS, "Plugin manifest")

        schema_version = data["schema_version"]
        if type(schema_version) is not int:
            raise PluginError("Plugin manifest schema_version must be an integer.")
        if schema_version != PLUGIN_SCHEMA_VERSION:
            raise PluginError(
                f"Unsupported plugin manifest schema_version: {schema_version!r}."
            )

        plugin = self._require_mapping(data["plugin"], "plugin")
        self._require_exact_keys(plugin, _PLUGIN_KEYS, "plugin")
        metadata = PluginMetadata(
            plugin_id=PluginId(self._require_string(plugin, "id")),
            name=self._require_string(plugin, "name"),
            version=PluginVersion(self._require_string(plugin, "version")),
            sdk_version=PluginSdkVersion(self._require_integer(plugin, "sdk_version")),
            description=self._require_string(plugin, "description"),
            entry_point=PluginEntryPoint(self._require_string(plugin, "entry_point")),
        )
        capabilities = tuple(
            PluginCapability(item)
            for item in self._read_string_items(
                plugin["capabilities"], "capabilities"
            )
        )
        permissions = tuple(
            PluginPermission(item)
            for item in self._read_string_items(
                plugin["permissions"], "permissions"
            )
        )
        dependencies = self._read_dependencies(
            plugin["dependencies"], metadata.plugin_id
        )
        return PluginManifest(
            schema_version=schema_version,
            metadata=metadata,
            capabilities=capabilities,
            permissions=permissions,
            dependencies=dependencies,
        )

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return read_yaml(path)
        except yaml.YAMLError as exc:
            raise PluginError("Plugin manifest YAML is malformed.") from exc
        except (EngineeringError, OSError, TypeError, UnicodeError) as exc:
            raise PluginError(f"Plugin manifest could not be read: {exc}") from exc

    @classmethod
    def _reject_secret_keys(cls, value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_text = str(key)
                path = f"{prefix}.{key_text}" if prefix else key_text
                normalized = key_text.lower().replace("-", "_")
                if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
                    raise PluginError(
                        f"Secret-like manifest field is not allowed: {path}."
                    )
                cls._reject_secret_keys(nested, path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                cls._reject_secret_keys(nested, f"{prefix}[{index}]")

    @staticmethod
    def _require_exact_keys(
        data: dict[str, Any], expected: frozenset[str], label: str
    ) -> None:
        if not all(isinstance(key, str) for key in data):
            raise PluginError(f"{label} keys must be strings.")
        keys = set(data)
        missing = sorted(expected - keys)
        unexpected = sorted(keys - expected)
        if missing:
            raise PluginError(f"{label} is missing keys: {', '.join(missing)}.")
        if unexpected:
            raise PluginError(
                f"{label} contains unknown keys: {', '.join(unexpected)}."
            )

    @staticmethod
    def _require_mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise PluginError(f"{label} must be a mapping.")
        if not all(isinstance(key, str) for key in value):
            raise PluginError(f"{label} keys must be strings.")
        return value

    @staticmethod
    def _require_string(data: dict[str, Any], field: str) -> str:
        value = data[field]
        if not isinstance(value, str):
            raise PluginError(f"plugin.{field} must be a string.")
        return value

    @staticmethod
    def _require_integer(data: dict[str, Any], field: str) -> int:
        value = data[field]
        if type(value) is not int:
            raise PluginError(f"plugin.{field} must be an integer.")
        return value

    @staticmethod
    def _read_string_items(value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise PluginError(f"plugin.{field} must be a list.")
        if not all(isinstance(item, str) for item in value):
            raise PluginError(f"plugin.{field} entries must be strings.")
        if len(set(value)) != len(value):
            raise PluginError(f"plugin.{field} contains duplicate entries.")
        return tuple(sorted(value))

    @classmethod
    def _read_dependencies(
        cls, value: object, owner_id: PluginId
    ) -> tuple[PluginDependency, ...]:
        if not isinstance(value, list):
            raise PluginError("plugin.dependencies must be a list.")
        dependencies: list[PluginDependency] = []
        seen: set[str] = set()
        for index, raw in enumerate(value):
            dependency = cls._require_mapping(
                raw, f"plugin.dependencies[{index}]"
            )
            cls._require_exact_keys(
                dependency, _DEPENDENCY_KEYS, f"plugin.dependencies[{index}]"
            )
            dependency_id = dependency["id"]
            version = dependency["version"]
            if not isinstance(dependency_id, str) or not isinstance(version, str):
                raise PluginError(
                    f"plugin.dependencies[{index}] id and version must be strings."
                )
            parsed = PluginDependency(PluginId(dependency_id), version)
            if parsed.plugin_id == owner_id:
                raise PluginError("A plugin cannot depend on itself.")
            if dependency_id in seen:
                raise PluginError(f"Duplicate plugin dependency: {dependency_id}.")
            seen.add(dependency_id)
            dependencies.append(parsed)
        return tuple(
            sorted(dependencies, key=lambda item: item.plugin_id.value)
        )
