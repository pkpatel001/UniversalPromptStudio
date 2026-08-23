"""Strict, non-executing schema-1 theme manifest reader."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from Engineering.core.exceptions import EngineeringError, ThemeError
from Engineering.core.filesystem import read_yaml

from .models import (
    ThemeAppearance,
    ThemeColor,
    ThemeId,
    ThemeManifest,
    ThemeMetadata,
    ThemePalette,
    ThemeSdkVersion,
    ThemeVersion,
)

THEME_MANIFEST_NAME = "theme-manifest.yaml"
THEME_SCHEMA_VERSION = 1
THEME_SDK_API_LEVEL = 1

_ROOT_KEYS = frozenset({"schema_version", "theme"})
_THEME_KEYS = frozenset(
    {
        "id",
        "name",
        "version",
        "sdk_version",
        "description",
        "default_appearance",
        "palettes",
    }
)
_PALETTE_KEYS = frozenset({"appearance", "colors"})
_COLOR_KEYS = frozenset(
    {
        "canvas",
        "surface",
        "surface_muted",
        "text",
        "text_muted",
        "border",
        "primary",
        "primary_text",
        "sidebar",
        "sidebar_text",
        "focus",
    }
)
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class ThemeManifestReader:
    """Parse declarative theme metadata without loading assets or applying styles."""

    def detect_schema_version(self, path: Path) -> int:
        data = self._read(path)
        value = data.get("schema_version")
        if type(value) is not int:
            raise ThemeError("Theme manifest schema_version must be an integer.")
        return value

    def read(self, path: Path) -> ThemeManifest:
        return self._parse(self._read(path))

    def read_text(self, content: str) -> ThemeManifest:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ThemeError("Theme manifest YAML is malformed.") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ThemeError("Theme manifest could not be read: YAML root must be a mapping.")
        return self._parse(data)

    def _parse(self, data: dict[str, Any]) -> ThemeManifest:
        self._reject_secret_keys(data)
        self._require_exact_keys(data, _ROOT_KEYS, "Theme manifest")
        schema_version = data["schema_version"]
        if type(schema_version) is not int:
            raise ThemeError("Theme manifest schema_version must be an integer.")
        if schema_version != THEME_SCHEMA_VERSION:
            raise ThemeError(f"Unsupported theme manifest schema_version: {schema_version!r}.")
        theme = self._require_mapping(data["theme"], "theme")
        self._require_exact_keys(theme, _THEME_KEYS, "theme")
        default = self._read_enum(
            ThemeAppearance,
            theme["default_appearance"],
            "theme.default_appearance",
        )
        return ThemeManifest(
            schema_version,
            ThemeMetadata(
                ThemeId(self._require_string(theme, "id", "theme")),
                self._require_string(theme, "name", "theme"),
                ThemeVersion(self._require_string(theme, "version", "theme")),
                ThemeSdkVersion(self._require_integer(theme, "sdk_version", "theme")),
                self._require_string(theme, "description", "theme"),
            ),
            default,
            self._read_palettes(theme["palettes"]),
        )

    def _read_palettes(self, value: object) -> tuple[ThemePalette, ...]:
        if not isinstance(value, list):
            raise ThemeError("theme.palettes must be a list.")
        palettes = []
        for index, item in enumerate(value):
            label = f"theme.palettes[{index}]"
            palette = self._require_mapping(item, label)
            self._require_exact_keys(palette, _PALETTE_KEYS, label)
            colors = self._require_mapping(palette["colors"], f"{label}.colors")
            self._require_exact_keys(colors, _COLOR_KEYS, f"{label}.colors")
            palettes.append(
                ThemePalette(
                    appearance=self._read_enum(
                        ThemeAppearance,
                        palette["appearance"],
                        f"{label}.appearance",
                    ),
                    **{
                        name: ThemeColor(self._require_string(colors, name, f"{label}.colors"))
                        for name in sorted(_COLOR_KEYS)
                    },
                )
            )
        return tuple(sorted(palettes, key=lambda item: item.appearance.value))

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            return read_yaml(path)
        except yaml.YAMLError as exc:
            raise ThemeError("Theme manifest YAML is malformed.") from exc
        except (EngineeringError, OSError, TypeError, UnicodeError) as exc:
            raise ThemeError(f"Theme manifest could not be read: {exc}") from exc

    @classmethod
    def _reject_secret_keys(cls, value: object, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                key_text = str(key)
                path = f"{prefix}.{key_text}" if prefix else key_text
                normalized = key_text.lower().replace("-", "_")
                if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
                    raise ThemeError(
                        f"Secret-like theme manifest field is not allowed: {path}."
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
            raise ThemeError(f"{label} keys must be strings.")
        missing = sorted(expected - set(data))
        unexpected = sorted(set(data) - expected)
        if missing:
            raise ThemeError(f"{label} is missing keys: {', '.join(missing)}.")
        if unexpected:
            raise ThemeError(f"{label} contains unknown keys: {', '.join(unexpected)}.")

    @staticmethod
    def _require_mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            raise ThemeError(f"{label} must be a mapping with string keys.")
        return value

    @staticmethod
    def _require_string(data: dict[str, Any], field: str, prefix: str) -> str:
        value = data[field]
        if not isinstance(value, str):
            raise ThemeError(f"{prefix}.{field} must be a string.")
        return value

    @staticmethod
    def _require_integer(data: dict[str, Any], field: str, prefix: str) -> int:
        value = data[field]
        if type(value) is not int:
            raise ThemeError(f"{prefix}.{field} must be an integer.")
        return value

    @staticmethod
    def _read_enum[T: StrEnum](enum_type: type[T], value: object, label: str) -> T:
        if not isinstance(value, str):
            raise ThemeError(f"{label} must be a string.")
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise ThemeError(f"{label} must be one of: {allowed}.") from exc


__all__ = [
    "THEME_MANIFEST_NAME",
    "THEME_SCHEMA_VERSION",
    "THEME_SDK_API_LEVEL",
    "ThemeManifestReader",
]
