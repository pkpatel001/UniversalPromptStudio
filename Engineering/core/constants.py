"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Global Constants

This module contains project-wide constants used throughout the
Engineering Toolkit.

Nothing in this file should perform I/O.

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Project Information
# ---------------------------------------------------------------------------

PROJECT_NAME: str = "Universal Prompt Studio"

PROJECT_SHORT_NAME: str = "UPS"

ENGINEERING_NAME: str = "Engineering Toolkit"

COMPANY_NAME: str = "The Patel Brothers Creative Solutions"

COPYRIGHT_YEAR: int = 2026

LICENSE_NAME: str = "Mozilla Public License 2.0"

PYTHON_MINIMUM_VERSION: tuple[int, int] = (3, 12)

# ---------------------------------------------------------------------------
# Folder Names
# ---------------------------------------------------------------------------

BACKEND_FOLDER = "Backend"

FRONTEND_FOLDER = "Frontend"

ENGINEERING_FOLDER = "Engineering"

DOCS_FOLDER = "Docs"

DATABASE_FOLDER = "Database"

PLUGINS_FOLDER = "Plugins"

THEMES_FOLDER = "Themes"

ASSETS_FOLDER = "Assets"

TEMPLATES_FOLDER = "Templates"

CATEGORIES_FOLDER = "Categories"

TESTS_FOLDER = "Tests"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ENCODING = "utf-8"

DEFAULT_CONFIG_FILENAME = "project.yaml"

DEFAULT_MANIFEST_FILENAME = "documentation_manifest.yaml"

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

DOCUMENTATION_ROOT = Path("Engineering") / "Documentation"

MANIFEST_FOLDER = DOCUMENTATION_ROOT / "Manifest"

RULES_FOLDER = DOCUMENTATION_ROOT / "Rules"

SCHEMA_FOLDER = DOCUMENTATION_ROOT / "Schemas"

TEMPLATE_FOLDER = DOCUMENTATION_ROOT / "Templates"

SCRIPT_FOLDER = DOCUMENTATION_ROOT / "Scripts"

GENERATED_FOLDER = DOCUMENTATION_ROOT / "Generated"

LOG_FOLDER = DOCUMENTATION_ROOT / "Logs"