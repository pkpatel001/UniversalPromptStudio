"""Deterministic E-015.4 runtime token compilation without theme application."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from Engineering.core.exceptions import ThemeError

from .models import (
    ThemeAppearance,
    ThemeColor,
    ThemeId,
    ThemeManifest,
    ThemePalette,
    ThemeVersion,
)

THEME_CSS_VARIABLE_PREFIX = "--ups-color-"


class ThemeTokenName(StrEnum):
    """Fixed host-recognized semantic color token names."""

    CANVAS = "canvas"
    SURFACE = "surface"
    SURFACE_MUTED = "surface-muted"
    TEXT = "text"
    TEXT_MUTED = "text-muted"
    BORDER = "border"
    PRIMARY = "primary"
    PRIMARY_TEXT = "primary-text"
    SIDEBAR = "sidebar"
    SIDEBAR_TEXT = "sidebar-text"
    FOCUS = "focus"


_PALETTE_FIELDS: dict[ThemeTokenName, str] = {
    ThemeTokenName.CANVAS: "canvas",
    ThemeTokenName.SURFACE: "surface",
    ThemeTokenName.SURFACE_MUTED: "surface_muted",
    ThemeTokenName.TEXT: "text",
    ThemeTokenName.TEXT_MUTED: "text_muted",
    ThemeTokenName.BORDER: "border",
    ThemeTokenName.PRIMARY: "primary",
    ThemeTokenName.PRIMARY_TEXT: "primary_text",
    ThemeTokenName.SIDEBAR: "sidebar",
    ThemeTokenName.SIDEBAR_TEXT: "sidebar_text",
    ThemeTokenName.FOCUS: "focus",
}


@dataclass(frozen=True, slots=True)
class ThemeToken:
    """One typed semantic token and its already-validated color value."""

    name: ThemeTokenName
    value: ThemeColor

    def __post_init__(self) -> None:
        if not isinstance(self.name, ThemeTokenName):
            raise ThemeError("Theme token name must be ThemeTokenName.")
        if not isinstance(self.value, ThemeColor):
            raise ThemeError("Theme token value must be ThemeColor.")

    @property
    def css_variable(self) -> str:
        return f"{THEME_CSS_VARIABLE_PREFIX}{self.name.value}"


@dataclass(frozen=True, slots=True)
class ThemeTokenSet:
    """Complete ordered tokens for one exact theme version and appearance."""

    theme_id: ThemeId
    version: ThemeVersion
    appearance: ThemeAppearance
    tokens: tuple[ThemeToken, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.theme_id, ThemeId):
            raise ThemeError("Theme token set theme_id must be ThemeId.")
        if not isinstance(self.version, ThemeVersion):
            raise ThemeError("Theme token set version must be ThemeVersion.")
        if not isinstance(self.appearance, ThemeAppearance):
            raise ThemeError("Theme token set appearance must be ThemeAppearance.")
        if not all(isinstance(item, ThemeToken) for item in self.tokens):
            raise ThemeError("Theme token set entries must be ThemeToken values.")
        expected = tuple(ThemeTokenName)
        actual = tuple(item.name for item in self.tokens)
        if actual != expected:
            raise ThemeError("Theme token set must contain every semantic token in host order.")

    def value_for(self, name: ThemeTokenName) -> ThemeColor:
        """Return one token value from the bounded complete set."""

        if not isinstance(name, ThemeTokenName):
            raise ThemeError("Theme token lookup name must be ThemeTokenName.")
        return self.tokens[tuple(ThemeTokenName).index(name)].value


class ThemeTokenCompiler:
    """Compile one validated manifest palette into fixed runtime tokens."""

    def compile(
        self,
        manifest: ThemeManifest,
        appearance: ThemeAppearance | None = None,
    ) -> ThemeTokenSet:
        if not isinstance(manifest, ThemeManifest):
            raise ThemeError("Theme token compilation requires ThemeManifest.")
        selected = appearance or manifest.default_appearance
        if not isinstance(selected, ThemeAppearance):
            raise ThemeError("Theme token appearance must be ThemeAppearance.")
        palette = self._select_palette(manifest, selected)
        tokens = tuple(
            ThemeToken(name, cast(ThemeColor, getattr(palette, field_name)))
            for name, field_name in _PALETTE_FIELDS.items()
        )
        return ThemeTokenSet(
            manifest.metadata.theme_id,
            manifest.metadata.version,
            selected,
            tokens,
        )

    @staticmethod
    def _select_palette(
        manifest: ThemeManifest,
        appearance: ThemeAppearance,
    ) -> ThemePalette:
        for palette in manifest.palettes:
            if palette.appearance == appearance:
                return palette
        raise ThemeError(
            f"Theme {manifest.metadata.theme_id.value} version "
            f"{manifest.metadata.version.value} has no {appearance.value} palette."
        )


class ThemeCssVariableSerializer:
    """Serialize fixed validated tokens as selector-free CSS declarations."""

    def serialize(self, token_set: ThemeTokenSet) -> str:
        if not isinstance(token_set, ThemeTokenSet):
            raise ThemeError("CSS variable serialization requires ThemeTokenSet.")
        return "\n".join(
            f"{token.css_variable}: {token.value.value};" for token in token_set.tokens
        )


__all__ = [
    "THEME_CSS_VARIABLE_PREFIX",
    "ThemeCssVariableSerializer",
    "ThemeToken",
    "ThemeTokenCompiler",
    "ThemeTokenName",
    "ThemeTokenSet",
]
