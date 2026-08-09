"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Template Subsystem

This module provides the template abstraction for the Code Generation
framework. It defines:

* Template — immutable template model
* TemplateRepository — ABC for resolving template identifiers
* DirectoryTemplateRepository — disk-based template repository
* auto_generated_header — language-aware header generation

Templates are stored on disk as ``.j2`` files and resolved by a
hierarchical identifier (e.g. ``python.module`` → ``<root>/python/module.j2``).

Public API
----------
from Engineering.CodeGeneration.templates import (
    Template,
    TemplateRepository,
    DirectoryTemplateRepository,
    auto_generated_header,
)

===============================================================================
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from Engineering.core.exceptions import TemplateNotFoundError
from Engineering.core.filesystem import read_text

__all__ = [
    "Template",
    "TemplateRepository",
    "DirectoryTemplateRepository",
    "auto_generated_header",
]

_TEMPLATE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


# ---------------------------------------------------------------------------
# Template Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Template:
    """
    An immutable, fully resolved template ready for rendering.

    Attributes
    ----------
    template_id
        Dot-separated identifier (e.g. ``python.module``).
    name
        Short name derived from the file stem.
    source
        Template source text (Jinja2 syntax).
    language
        Language category derived from the directory component.
    metadata
        Optional metadata about the template.
    """

    template_id: str
    name: str
    source: str
    language: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Template Repository
# ---------------------------------------------------------------------------


class TemplateRepository(ABC):
    """
    Abstract base class for resolving template identifiers to Template objects.
    """

    @abstractmethod
    def resolve(self, template_id: str) -> Template:
        """
        Resolve a template identifier to a Template.

        Raises
        ------
        TemplateNotFoundError
            If the template cannot be resolved.
        """

    @abstractmethod
    def contains(self, template_id: str) -> bool:
        """Return True if a template with this identifier exists."""

    @abstractmethod
    def template_ids(self) -> tuple[str, ...]:
        """Return all available template identifiers, sorted."""


# ---------------------------------------------------------------------------
# Directory Template Repository
# ---------------------------------------------------------------------------


class DirectoryTemplateRepository(TemplateRepository):
    """
    Resolves templates from a directory tree on disk.

    Convention
    ----------
    Templates are stored as ``.j2`` files. The identifier is resolved
    by replacing dots with path separators and appending ``.j2``:

    ``python.module`` → ``<root>/python/module.j2``

    The language is derived from the first directory component
    of the resolved path relative to the root.
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        """Return the resolved repository root."""

        return self._root

    def _id_to_path(self, template_id: str) -> Path:
        """Convert a template identifier to a filesystem path."""

        relative = template_id.replace(".", "/") + ".j2"
        return self._root / relative

    def _validate_id(self, template_id: str) -> None:
        """Validate a template identifier format."""

        if not _TEMPLATE_ID_PATTERN.match(template_id):
            raise TemplateNotFoundError(
                f"Invalid template identifier format: {template_id!r}"
            )

    def resolve(self, template_id: str) -> Template:
        """
        Resolve a template identifier to a Template from disk.

        Parameters
        ----------
        template_id
            Dot-separated template identifier.

        Returns
        -------
        Template
            Resolved template with source loaded from disk.

        Raises
        ------
        TemplateNotFoundError
            If the identifier is invalid, the file does not exist,
            or the path escapes the repository root.
        """

        self._validate_id(template_id)

        path = self._id_to_path(template_id)

        resolved = path.resolve()
        if not str(resolved).startswith(str(self._root)):
            raise TemplateNotFoundError(
                f"Template path escapes repository root: {template_id!r}"
            )

        if not resolved.is_file():
            raise TemplateNotFoundError(
                f"Template not found: {template_id!r} ({resolved})"
            )

        source = read_text(resolved)
        parts = template_id.split(".")
        language = parts[0] if len(parts) > 1 else ""
        name = parts[-1]

        return Template(
            template_id=template_id,
            name=name,
            source=source,
            language=language,
            metadata={"language": language, "path": resolved.as_posix()},
        )

    def contains(self, template_id: str) -> bool:
        """Return True if the template file exists on disk."""

        try:
            self._validate_id(template_id)
            return self._id_to_path(template_id).resolve().is_file()
        except TemplateNotFoundError:
            return False

    def template_ids(self) -> tuple[str, ...]:
        """Return all template identifiers discovered under the root."""

        if not self._root.is_dir():
            return ()

        ids: list[str] = []
        for path in sorted(self._root.rglob("*.j2")):
            if not path.is_file():
                continue
            relative = path.relative_to(self._root).as_posix()
            if relative.endswith(".j2"):
                relative = relative[:-3]
            template_id = relative.replace("/", ".")
            if _TEMPLATE_ID_PATTERN.match(template_id):
                ids.append(template_id)

        return tuple(ids)


# ---------------------------------------------------------------------------
# Auto-Generated Header Utility
# ---------------------------------------------------------------------------

_LANGUAGE_COMMENT_PREFIXES: Mapping[str, str] = {
    "python": "#",
    "yaml": "#",
    "markdown": "#",
    "json": "",
    "html": "",
    "javascript": "//",
    "toml": "#",
}

_BLOCK_COMMENT_LANGUAGES: set[str] = {"html"}


def auto_generated_header(
    language: str = "python",
    generator_id: str = "",
    template_id: str = "",
    source: str = "",
) -> str:
    """
    Return a language-aware auto-generated file header string.

    Parameters
    ----------
    language
        Target language for comment style detection.
    generator_id
        Optional generator identifier to include.
    template_id
        Optional template identifier to include.
    source
        Optional source description.

    Returns
    -------
    str
        Header string ready to prepend to generated content.
    """

    separator = "==============================================================================="

    content_lines = [
        "AUTO-GENERATED FILE",
    ]

    if generator_id:
        content_lines.append(f"Generator: {generator_id}")
    if template_id:
        content_lines.append(f"Template: {template_id}")
    if source:
        content_lines.append(f"Source: {source}")

    content_lines.append("DO NOT EDIT DIRECTLY.")

    if language in _BLOCK_COMMENT_LANGUAGES:
        lines = ["<!--", separator]
        for line in content_lines:
            lines.append(line)
        lines.append(separator)
        lines.append("-->")
        return "\n".join(lines) + "\n"

    prefix = _LANGUAGE_COMMENT_PREFIXES.get(language, "#")

    lines = [f"{prefix}{separator}"]
    for line in content_lines:
        lines.append(f"{prefix}{line}" if prefix else line)
    lines.append(f"{prefix}{separator}")

    return "\n".join(lines) + "\n"
