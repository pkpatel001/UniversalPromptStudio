"""Immutable E-015.1 theme SDK metadata models."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum

from packaging.version import InvalidVersion, Version

from Engineering.core.exceptions import ThemeError

from .validation import require_hex_color, require_nonempty_text, require_theme_id


@dataclass(frozen=True, slots=True)
class ThemeId:
    """Stable vendor-qualified theme identity."""

    value: str

    def __post_init__(self) -> None:
        require_theme_id(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ThemeVersion:
    """Canonical PEP 440 theme implementation version."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise ThemeError(
                "Theme version must be a non-empty value of at most 64 characters."
            )
        try:
            parsed = Version(self.value)
        except InvalidVersion as exc:
            raise ThemeError(f"Invalid theme version: {self.value!r}") from exc
        if (
            str(parsed) != self.value
            or len(parsed.release) != 3
            or parsed.epoch != 0
            or parsed.local is not None
        ):
            raise ThemeError(
                "Theme version must use canonical PEP 440 form with exactly "
                "major.minor.patch release components and no epoch or local version."
            )

    @property
    def parsed(self) -> Version:
        return Version(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ThemeSdkVersion:
    """Positive UPS Theme SDK API level."""

    api_level: int

    def __post_init__(self) -> None:
        if type(self.api_level) is not int or self.api_level < 1:
            raise ThemeError("Theme sdk_version must be a positive integer API level.")


class ThemeAppearance(StrEnum):
    """Host-recognized visual appearance categories."""

    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high-contrast"


@dataclass(frozen=True, slots=True)
class ThemeColor:
    """One opaque portable color value."""

    value: str

    def __post_init__(self) -> None:
        require_hex_color(self.value, "Theme color")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Required semantic colors for one appearance."""

    appearance: ThemeAppearance
    canvas: ThemeColor
    surface: ThemeColor
    surface_muted: ThemeColor
    text: ThemeColor
    text_muted: ThemeColor
    border: ThemeColor
    primary: ThemeColor
    primary_text: ThemeColor
    sidebar: ThemeColor
    sidebar_text: ThemeColor
    focus: ThemeColor

    def __post_init__(self) -> None:
        if not isinstance(self.appearance, ThemeAppearance):
            raise ThemeError("Theme palette appearance must be ThemeAppearance.")
        for field in fields(self):
            if field.name != "appearance" and not isinstance(
                getattr(self, field.name), ThemeColor
            ):
                raise ThemeError(f"Theme palette {field.name} must be ThemeColor.")


@dataclass(frozen=True, slots=True)
class ThemeMetadata:
    """Portable identity and descriptive theme metadata."""

    theme_id: ThemeId
    name: str
    version: ThemeVersion
    sdk_version: ThemeSdkVersion
    description: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.name, "Theme name", maximum=120)
        require_nonempty_text(self.description, "Theme description", maximum=1000)


@dataclass(frozen=True, slots=True)
class ThemeManifest:
    """Canonical schema-1 declarative theme document."""

    schema_version: int
    metadata: ThemeMetadata
    default_appearance: ThemeAppearance
    palettes: tuple[ThemePalette, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ThemeError("Theme manifest schema_version must be integer 1.")
        if not isinstance(self.default_appearance, ThemeAppearance):
            raise ThemeError("Theme default_appearance must be ThemeAppearance.")
        if not self.palettes:
            raise ThemeError("Theme manifest must declare at least one palette.")
        appearances = tuple(item.appearance for item in self.palettes)
        if len(set(appearances)) != len(appearances):
            raise ThemeError("Theme manifest palette appearances must be unique.")
        if self.default_appearance not in appearances:
            raise ThemeError("Theme default_appearance must have a matching palette.")


__all__ = [
    "ThemeAppearance",
    "ThemeColor",
    "ThemeId",
    "ThemeManifest",
    "ThemeMetadata",
    "ThemePalette",
    "ThemeSdkVersion",
    "ThemeVersion",
]
