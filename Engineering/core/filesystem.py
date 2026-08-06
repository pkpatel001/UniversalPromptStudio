"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Filesystem Utilities

This module provides centralized filesystem helper functions used throughout
the Engineering Toolkit.

All file and directory operations should be performed through this module
rather than directly using pathlib in higher-level infrastructure.

Responsibilities
----------------
* Reading and writing UTF-8 text files
* Reading and writing binary files
* Reading and writing YAML
* Reading and writing JSON
* Creating directories
* Creating parent directories automatically
* Basic filesystem queries

This module intentionally contains no project-specific business logic.

===============================================================================
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .constants import (
    DEFAULT_ENCODING,
    DEFAULT_JSON_ENSURE_ASCII,
    DEFAULT_JSON_INDENT,
    DEFAULT_YAML_ALLOW_UNICODE,
    DEFAULT_YAML_INDENT,
    DEFAULT_YAML_SORT_KEYS,
)

__all__ = [
    "ensure_directory",
    "exists",
    "is_directory",
    "is_file",
    "read_bytes",
    "read_json",
    "read_text",
    "read_yaml",
    "write_bytes",
    "write_json",
    "write_text",
    "write_yaml",
]

# -----------------------------------------------------------------------------
# Directory Utilities
# -----------------------------------------------------------------------------


def ensure_directory(directory: Path) -> Path:
    """
    Ensure that a directory exists.

    Missing parent directories are created automatically.

    Parameters
    ----------
    directory
        Directory to create.

    Returns
    -------
    Path
        The same directory path.
    """

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _ensure_parent_directory(path: Path) -> Path:
    """
    Ensure that the parent directory of a file exists.

    Parameters
    ----------
    path
        Target file path.

    Returns
    -------
    Path
        The parent directory.
    """

    return ensure_directory(path.parent)


# -----------------------------------------------------------------------------
# Filesystem Queries
# -----------------------------------------------------------------------------


def exists(path: Path) -> bool:
    """
    Return whether a filesystem path exists.

    Parameters
    ----------
    path
        Filesystem path.

    Returns
    -------
    bool
    """

    return path.exists()


def is_file(path: Path) -> bool:
    """
    Return whether the path refers to a regular file.
    """

    return path.is_file()


def is_directory(path: Path) -> bool:
    """
    Return whether the path refers to a directory.
    """

    return path.is_dir()


# -----------------------------------------------------------------------------
# Text Files
# -----------------------------------------------------------------------------

from .exceptions import FileReadError

def read_text(path: Path) -> str:
    """
    Read a UTF-8 encoded text file.

    Parameters
    ----------
    path
        File to read.

    Returns
    -------
    str
        File contents.
    """
    try:
        return path.read_text(encoding=DEFAULT_ENCODING)
    except OSError as exc:
        raise FileReadError(
            f"Failed to read file: {path}"
        ) from exc

from .exceptions import FileWriteError

def write_text(path: Path, text: str) -> None:
    """
    Write a UTF-8 encoded text file.

    Parent directories are created automatically.

    Parameters
    ----------
    path
        Destination file.

    text
        Text to write.
    """

    _ensure_parent_directory(path)

    try:
        return path.write_text(
            text,
            encoding=DEFAULT_ENCODING,
        )
    except OSError as exc:
        raise FileWriteError(
            f"Failed to write file: {path}"
        ) from exc


# -----------------------------------------------------------------------------
# Binary Files
# -----------------------------------------------------------------------------


def read_bytes(path: Path) -> bytes:
    """
    Read a binary file.

    Parameters
    ----------
    path
        File to read.

    Returns
    -------
    bytes
    """

    return path.read_bytes()


def write_bytes(path: Path, data: bytes) -> None:
    """
    Write a binary file.

    Parent directories are created automatically.

    Parameters
    ----------
    path
        Destination file.

    data
        Binary data.
    """

    _ensure_parent_directory(path)

    path.write_bytes(data)


# -----------------------------------------------------------------------------
# YAML
# -----------------------------------------------------------------------------


def read_yaml(path: Path) -> dict[str, Any]:
    """
    Read a YAML mapping.

    Empty YAML files return an empty dictionary.

    Parameters
    ----------
    path
        YAML file.

    Returns
    -------
    dict[str, Any]
    """

    data = yaml.safe_load(read_text(path))

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise TypeError(
            "YAML root object must be a mapping."
        )

    return data


def write_yaml(
    path: Path,
    data: Mapping[str, Any],
) -> None:
    """
    Write a YAML mapping.

    Parameters
    ----------
    path
        Destination YAML file.

    data
        Mapping to serialize.
    """

    _ensure_parent_directory(path)

    yaml_text = yaml.safe_dump(
    data,
    sort_keys=DEFAULT_YAML_SORT_KEYS,
    allow_unicode=DEFAULT_YAML_ALLOW_UNICODE,
    indent=DEFAULT_YAML_INDENT,
    )

    write_text(
        path,
        yaml_text,
    )


# -----------------------------------------------------------------------------
# JSON
# -----------------------------------------------------------------------------


def read_json(path: Path) -> dict[str, Any]:
    """
    Read a JSON object.

    Parameters
    ----------
    path
        JSON file.

    Returns
    -------
    dict[str, Any]
    """

    data = json.loads(read_text(path))

    if not isinstance(data, dict):
        raise TypeError(
            "JSON root object must be an object."
        )

    return data


def write_json(
    path: Path,
    data: Mapping[str, Any],
) -> None:
    """
    Write a JSON object.

    Parameters
    ----------
    path
        Destination JSON file.

    data
        Object to serialize.
    """

    _ensure_parent_directory(path)

    write_text(
        path,
        json.dumps(
        data,
        indent=DEFAULT_JSON_INDENT,
        ensure_ascii=DEFAULT_JSON_ENSURE_ASCII,
        ),
    )