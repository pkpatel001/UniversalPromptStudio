"""Narrow validation helpers for non-executing AI-provider metadata."""

from __future__ import annotations

import re

from Engineering.core.exceptions import ProviderError

_PROVIDER_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$")
_ENTRY_POINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*" r":[A-Za-z_][A-Za-z0-9_]*$"
)
_METADATA_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")


def require_provider_id(value: str) -> str:
    """Validate one stable, vendor-qualified provider identifier."""

    if len(value) > 128 or not _PROVIDER_ID.fullmatch(value):
        raise ProviderError(
            "Provider id must be 1-128 lowercase characters in at least two "
            "dot-separated segments; hyphens are allowed within segments."
        )
    return value


def require_entry_point(value: str) -> str:
    """Validate module.path:ClassName syntax without importing it."""

    if len(value) > 256 or not _ENTRY_POINT.fullmatch(value):
        raise ProviderError("Provider entry_point must use module.path:ClassName syntax.")
    return value


def require_nonempty_text(value: str, label: str, *, maximum: int) -> str:
    """Validate bounded text without silently normalizing it."""

    if not value or value != value.strip() or len(value) > maximum:
        raise ProviderError(
            f"{label} must be non-empty, trimmed text of at most {maximum} characters."
        )
    return value


def require_metadata_id(value: str, label: str) -> str:
    """Validate a stable discovery-root label."""

    if len(value) > 128 or not _METADATA_ID.fullmatch(value):
        raise ProviderError(f"{label} must be a lowercase dot- or hyphen-separated identifier.")
    return value
