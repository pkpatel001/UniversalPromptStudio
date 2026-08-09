"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Generation Safety Policies

This module provides path safety validation for the Code Generation
framework. It prevents:

* Path traversal (``../../`` escapes)
* Writing outside the project boundary
* Writing to protected locations
* Serialization of secret values into context

Public API
----------
from Engineering.CodeGeneration.policies import validate_destination, validate_no_secrets

resolved = validate_destination(destination_root, relative_path, project_root)
validate_no_secrets(context_values)

===============================================================================
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from Engineering.core.exceptions import SecretContextError, UnsafeDestinationError

__all__ = [
    "SENSITIVE_KEY_PATTERNS",
    "DEFAULT_PROTECTED_PATHS",
    "validate_destination",
    "validate_no_secrets",
]

SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "private_key",
    "access_key",
    "auth",
)

DEFAULT_PROTECTED_PATHS: tuple[str, ...] = (
    ".git",
    "__pycache__",
)


def validate_destination(
    destination_root: Path,
    relative_path: str,
    project_root: Path,
) -> Path:
    """
    Validate and resolve an artifact destination path.

    Parameters
    ----------
    destination_root
        The root directory for generated artifacts.
    relative_path
        The relative path of the artifact within the generation root.
    project_root
        The project root directory (used as the boundary).

    Returns
    -------
    Path
        The resolved absolute destination path.

    Raises
    ------
    UnsafeDestinationError
        If the path violates safety rules.
    """

    if not relative_path:
        raise UnsafeDestinationError(
            "Artifact relative path must not be empty."
        )

    if os.sep in relative_path or "/" in relative_path:
        parts = Path(relative_path).parts
    else:
        parts = (relative_path,)

    for part in parts:
        if part in (".", "..", ""):
            raise UnsafeDestinationError(
                f"Artifact path contains traversal component: {part!r} "
                f"in {relative_path!r}"
            )

    resolved_root = destination_root.resolve()
    resolved_project = project_root.resolve()

    candidate = (resolved_root / relative_path).resolve()

    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafeDestinationError(
            f"Artifact destination escapes generation root: {relative_path!r}"
        ) from exc

    try:
        candidate.relative_to(resolved_project)
    except ValueError as exc:
        raise UnsafeDestinationError(
            f"Artifact destination escapes project root: {relative_path!r}. "
            f"Set allow_outside_project=True to override."
        ) from exc

    for protected in DEFAULT_PROTECTED_PATHS:
        if protected in candidate.parts:
            raise UnsafeDestinationError(
                f"Artifact destination references protected path: {protected!r} "
                f"in {relative_path!r}"
            )

    return candidate


def validate_no_secrets(values: Mapping[str, object]) -> None:
    """
    Validate that generation context values do not contain secret patterns.

    Refuses non-empty values whose keys match known sensitive key patterns.
    This prevents accidental serialization of secrets into generated artifacts.

    Parameters
    ----------
    values
        Context values to validate.

    Raises
    ------
    SecretContextError
        If a sensitive value is detected.
    """

    for key, value in values.items():
        normalized = key.lower().replace("-", "_").replace(" ", "_")
        for pattern in SENSITIVE_KEY_PATTERNS:
            if normalized == pattern or normalized.endswith(f"_{pattern}"):
                if value is not None and value != "" and value != 0 and value is not False:
                    raise SecretContextError(
                        f"Context value with sensitive key {key!r} "
                        f"must not contain actual secret values. "
                        f"Use an empty string or placeholder instead."
                    )
