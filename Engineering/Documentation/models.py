"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation Domain Model

This module defines the immutable domain model for generated documentation.

The model is intentionally minimal, providing a clean separation between
source analysis and rendering. It does not attempt to model every possible
documentation structure, but rather provides the abstractions needed by
the current documentation generator.

Public API
----------
from Engineering.Documentation.models import (
    DocumentationDocument,
    DocumentationSection,
    DocumentationElement,
    DocumentationElementKind,
    DocumentationMetadata,
    DocumentationReport,
    GeneratedDocument,
    FailedDocument,
)

===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DocumentationElementKind",
    "DocumentationElement",
    "DocumentationSection",
    "DocumentationDocument",
    "DocumentationMetadata",
    "GeneratedDocument",
    "FailedDocument",
    "DocumentationReport",
]


# -----------------------------------------------------------------------------
# Element Kind
# -----------------------------------------------------------------------------


class DocumentationElementKind(Enum):
    """
    Types of content elements that can appear in a documentation section.
    """

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    LINK = "link"
    SEPARATOR = "separator"


# -----------------------------------------------------------------------------
# Documentation Element
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentationElement:
    """
    A single content element within a documentation section.

    Elements are the atomic units of documentation content. Each element
    has a kind that determines how it is rendered.
    """

    kind: DocumentationElementKind
    content: str = ""
    items: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    level: int = 0


# -----------------------------------------------------------------------------
# Documentation Section
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentationSection:
    """
    A named section of a documentation document.

    Sections contain ordered elements and may have a heading level.
    """

    title: str
    level: int = 2
    elements: tuple[DocumentationElement, ...] = ()


# -----------------------------------------------------------------------------
# Documentation Document
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentationDocument:
    """
    A complete documentation document ready for rendering.

    Documents contain metadata, sections, and are identified by a
    unique identifier within the generated documentation set.
    """

    identifier: str
    title: str
    description: str = ""
    metadata: DocumentationMetadata | None = None
    sections: tuple[DocumentationSection, ...] = ()


# -----------------------------------------------------------------------------
# Documentation Metadata
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentationMetadata:
    """
    Metadata describing the source and generation context of a document.
    """

    source: str = ""
    generated_from: str = ""


# -----------------------------------------------------------------------------
# Generated Document Record
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    """
    Record of a single generated documentation file.
    """

    path: str
    identifier: str
    title: str


# -----------------------------------------------------------------------------
# Failed Document Record
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FailedDocument:
    """
    Record of a documentation file that failed to generate.
    """

    path: str
    identifier: str
    reason: str


# -----------------------------------------------------------------------------
# Documentation Report
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DocumentationReport:
    """
    Aggregated results from a documentation generation run.
    """

    generated: tuple[GeneratedDocument, ...] = ()
    skipped: tuple[str, ...] = ()
    failed: tuple[FailedDocument, ...] = ()
    output_root: str = ""
    success: bool = True

    @property
    def summary(self) -> str:
        """
        Return a human-readable summary of the documentation report.
        """

        gen_count = len(self.generated)
        skip_count = len(self.skipped)
        fail_count = len(self.failed)

        if not self.success:
            return (
                f"Documentation generation failed: "
                f"{gen_count} generated, {fail_count} failed."
            )

        parts = [f"{gen_count} document(s) generated"]
        if skip_count:
            parts.append(f"{skip_count} skipped")
        if fail_count:
            parts.append(f"{fail_count} failed")

        return "Documentation generation completed: " + ", ".join(parts) + "."
