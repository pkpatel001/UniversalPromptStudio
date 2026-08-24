"""Narrow validation helpers for passive workflow definitions."""

from __future__ import annotations

import re

from Engineering.core.exceptions import WorkflowError

_VENDOR_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$")
_LOCAL_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def require_vendor_id(value: str, label: str) -> str:
    """Validate a stable, vendor-qualified workflow or operation identity."""

    if len(value) > 128 or not _VENDOR_ID.fullmatch(value):
        raise WorkflowError(
            f"{label} must be 1-128 lowercase characters in at least two "
            "dot-separated segments; hyphens are allowed within segments."
        )
    return value


def require_local_id(value: str, label: str) -> str:
    """Validate one portable node or port identifier."""

    if len(value) > 64 or not _LOCAL_ID.fullmatch(value):
        raise WorkflowError(
            f"{label} must be a 1-64 character lowercase identifier; "
            "hyphens are allowed between alphanumeric segments."
        )
    return value


def require_nonempty_text(value: str, label: str, *, maximum: int) -> str:
    """Validate bounded text without silently normalizing it."""

    if not value or value != value.strip() or len(value) > maximum:
        raise WorkflowError(
            f"{label} must be non-empty, trimmed text of at most {maximum} characters."
        )
    return value
