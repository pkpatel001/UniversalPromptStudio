"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Path Management

This module is responsible for discovering the project root and providing
centralized, strongly-typed access to all major project directories.

All Engineering Toolkit components should obtain project paths through this
module rather than constructing filesystem paths manually.

===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .constants import (
    ASSETS_FOLDER,
    BACKEND_FOLDER,
    CATEGORIES_FOLDER,
    DATABASE_FOLDER,
    DOCS_FOLDER,
    ENGINEERING_FOLDER,
    FRONTEND_FOLDER,
    PLUGINS_FOLDER,
    TEMPLATES_FOLDER,
    TESTS_FOLDER,
)

# -----------------------------------------------------------------------------
# Project Root Discovery
# -----------------------------------------------------------------------------

PROJECT_MARKERS = (
    "pyproject.toml",
    ".git",
    "README.md",
)


class ProjectRootNotFoundError(RuntimeError):
    """Raised when the Universal Prompt Studio project root cannot be found."""


def discover_project_root() -> Path:
    """
    Discover the Universal Prompt Studio project root.

    The search starts from this file and walks upwards until a directory
    containing all required project markers is found.

    Returns
    -------
    Path
        Absolute path to the project root.

    Raises
    ------
    ProjectRootNotFoundError
        If the project root cannot be located.
    """

    current = Path(__file__).resolve()

    for candidate in [current.parent, *current.parents]:
        if all((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate

    raise ProjectRootNotFoundError(
        "Unable to locate the Universal Prompt Studio project root."
    )


# -----------------------------------------------------------------------------
# Project Paths
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """
    Immutable representation of the Universal Prompt Studio folder structure.
    """

    root: Path

    backend: Path
    frontend: Path
    engineering: Path
    docs: Path
    database: Path

    plugins: Path
    templates: Path
    assets: Path
    categories: Path
    tests: Path


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_paths() -> ProjectPaths:
    """
    Return the singleton ProjectPaths instance.

    The project root is discovered only once and cached for the lifetime of
    the process.
    """

    root = discover_project_root()

    return ProjectPaths(
        root=root,
        backend=root / BACKEND_FOLDER,
        frontend=root / FRONTEND_FOLDER,
        engineering=root / ENGINEERING_FOLDER,
        docs=root / DOCS_FOLDER,
        database=root / DATABASE_FOLDER,
        plugins=root / PLUGINS_FOLDER,
        templates=root / TEMPLATES_FOLDER,
        assets=root / ASSETS_FOLDER,
        categories=root / CATEGORIES_FOLDER,
        tests=root / TESTS_FOLDER,
    )


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------


def verify_structure() -> list[str]:
    """
    Verify that the expected project folder structure exists.

    Returns
    -------
    list[str]
        A list of validation error messages.
        An empty list indicates success.
    """

    paths = get_paths()

    required = {
        "Backend": paths.backend,
        "Frontend": paths.frontend,
        "Engineering": paths.engineering,
        "Docs": paths.docs,
        "Database": paths.database,
        "Plugins": paths.plugins,
        "Templates": paths.templates,
        "Assets": paths.assets,
        "Categories": paths.categories,
        "Tests": paths.tests,
    }

    errors: list[str] = []

    for name, directory in required.items():
        if not directory.exists():
            errors.append(f"Missing required directory: {name}")

    return errors