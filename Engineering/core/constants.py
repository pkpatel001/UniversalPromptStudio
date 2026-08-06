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

BACKEND_FOLDER: str = "Backend"

FRONTEND_FOLDER: str = "Frontend"

ENGINEERING_FOLDER: str = "Engineering"

CONFIG_FOLDER: str = "config"

DOCS_FOLDER: str = "Docs"

DATABASE_FOLDER: str = "Database"

PLUGINS_FOLDER: str = "Plugins"

THEMES_FOLDER: str = "Themes"

ASSETS_FOLDER: str = "Assets"

TEMPLATES_FOLDER: str = "Templates"

CATEGORIES_FOLDER: str = "Categories"

TESTS_FOLDER: str = "Tests"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ENCODING: str = "utf-8"

YAML_EXTENSION: str = ".yaml"

JSON_EXTENSION: str = ".json"

MARKDOWN_EXTENSION: str = ".md"

PROJECT_CONFIG_FILENAME: str = "project.yaml"

ENGINEERING_CONFIG_FILENAME: str = "engineering.yaml"

DOCUMENTATION_CONFIG_FILENAME: str = "documentation.yaml"

LOGGING_CONFIG_FILENAME: str = "logging.yaml"

DEFAULT_MANIFEST_FILENAME: str = "documentation_manifest.yaml"

DEFAULT_JSON_INDENT: int = 4

DEFAULT_JSON_ENSURE_ASCII: bool = False

DEFAULT_YAML_INDENT: int = 2

DEFAULT_YAML_SORT_KEYS: bool = False

DEFAULT_YAML_ALLOW_UNICODE: bool = True

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

DOCUMENTATION_ROOT: Path = Path("Engineering") / "Documentation"

MANIFEST_FOLDER: Path = DOCUMENTATION_ROOT / "Manifest"

RULES_FOLDER: Path = DOCUMENTATION_ROOT / "Rules"

SCHEMA_FOLDER: Path = DOCUMENTATION_ROOT / "Schemas"

TEMPLATE_FOLDER: Path = DOCUMENTATION_ROOT / "Templates"

SCRIPT_FOLDER: Path = DOCUMENTATION_ROOT / "Scripts"

GENERATED_FOLDER: Path = DOCUMENTATION_ROOT / "Generated"

LOG_FOLDER: Path = DOCUMENTATION_ROOT / "Logs"