"""Validation helpers for portable non-executing theme metadata."""

from __future__ import annotations

import re

from Engineering.core.exceptions import ThemeError

_THEME_ID = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$"
)
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def require_theme_id(value: str) -> str:
    """Validate one stable vendor-qualified theme identifier."""

    if len(value) > 128 or not _THEME_ID.fullmatch(value):
        raise ThemeError(
            "Theme id must be 1-128 lowercase characters in at least two "
            "dot-separated segments; hyphens are allowed within segments."
        )
    return value


def require_nonempty_text(value: str, label: str, *, maximum: int) -> str:
    """Validate bounded trimmed text."""

    if not value or value != value.strip() or len(value) > maximum:
        raise ThemeError(
            f"{label} must be non-empty, trimmed text of at most {maximum} characters."
        )
    return value


def require_hex_color(value: str, label: str) -> str:
    """Validate a portable opaque six-digit hexadecimal color."""

    if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value):
        raise ThemeError(f"{label} must be an opaque #RRGGBB hexadecimal color.")
    return value
