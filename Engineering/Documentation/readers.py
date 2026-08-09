"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation Source Readers

This module provides readers that extract information from authoritative
project sources for documentation generation. Readers are responsible
for collecting raw information; they do not render Markdown.

Public API
----------
from Engineering.Documentation.readers import (
    ProjectReader,
    StructureReader,
    ConfigurationReader,
)

===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Engineering.core.config import Configuration
    from Engineering.core.paths import ProjectPaths

__all__ = [
    "ProjectMetadata",
    "ProjectReader",
    "StructureNode",
    "StructureReader",
    "ConfigurationSection",
    "ConfigurationField",
    "ConfigurationReader",
]


# -----------------------------------------------------------------------------
# Project Metadata
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """
    Immutable project-level metadata derived from configuration.
    """

    name: str
    short_name: str
    company: str
    version: str
    license: str
    python_minimum: str
    engineering_version: str = ""


# -----------------------------------------------------------------------------
# Project Reader
# -----------------------------------------------------------------------------


class ProjectReader:
    """
    Reads project metadata from the Engineering Toolkit configuration
    and source tree.
    """

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        config: Configuration | None = None,
    ) -> None:
        from Engineering.core.config import get_config
        from Engineering.core.paths import get_paths
        from Engineering.core.version import VERSION

        self._paths = paths if paths is not None else get_paths()
        self._config = config if config is not None else get_config()
        self._engineering_version = VERSION

    def metadata(self) -> ProjectMetadata:
        """
        Return project metadata derived from configuration.
        """

        return ProjectMetadata(
            name=self._config.project.name,
            short_name=self._config.project.short_name,
            company=self._config.project.company,
            version=self._config.project.version,
            license=self._config.project.license,
            python_minimum=self._config.project.python.minimum_version,
            engineering_version=self._engineering_version,
        )

    def read_pyproject_toml(self) -> dict[str, str]:
        """
        Read selected fields from pyproject.toml as plain text.

        Returns a dictionary of field names to string values.
        Only non-sensitive, top-level metadata fields are extracted.
        """

        pyproject_path = self._paths.root / "pyproject.toml"
        if not pyproject_path.is_file():
            return {}

        from Engineering.core.filesystem import read_text

        text = read_text(pyproject_path)
        result: dict[str, str] = {}

        for line in text.splitlines():
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("["):
                key, _, value = stripped.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in {"name", "version", "description", "license", "requires-python"}:
                    result[key] = value

        return result


# -----------------------------------------------------------------------------
# Structure Node
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StructureNode:
    """
    A single node in the project structure tree.
    """

    name: str
    is_directory: bool
    children: tuple[StructureNode, ...] = ()
    depth: int = 0


# -----------------------------------------------------------------------------
# Structure Reader
# -----------------------------------------------------------------------------


EXCLUDED_DIRECTORIES: frozenset[str] = frozenset({
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".pytest-tmp",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
})


EXCLUDED_FILES: frozenset[str] = frozenset({
    ".gitignore",
    ".gitattributes",
    ".DS_Store",
    "Thumbs.db",
})


def _should_exclude(name: str) -> bool:
    """
    Return True if a file or directory name should be excluded from
    the project structure tree.
    """

    if name in EXCLUDED_DIRECTORIES:
        return True
    if name in EXCLUDED_FILES:
        return True
    if name.endswith(".pyc"):
        return True
    if name.endswith(".egg-info"):
        return True
    return False


class StructureReader:
    """
    Walks the project repository and produces a deterministic
    tree representation.
    """

    def __init__(self, paths: ProjectPaths | None = None) -> None:
        from Engineering.core.paths import get_paths

        self._paths = paths if paths is not None else get_paths()

    def read(self, max_depth: int = 3) -> StructureNode:
        """
        Read the project structure up to the specified depth.

        Parameters
        ----------
        max_depth
            Maximum directory depth to traverse. The root is depth 0.
        """

        return self._read_node(self._paths.root, depth=0, max_depth=max_depth)

    def _read_node(self, path: Path, depth: int, max_depth: int) -> StructureNode:
        """
        Recursively read a directory node.
        """

        name = path.name if path != self._paths.root else path.name

        if not path.is_dir():
            return StructureNode(
                name=name,
                is_directory=False,
                depth=depth,
            )

        children: list[StructureNode] = []

        if depth < max_depth:
            try:
                entries = sorted(
                    path.iterdir(),
                    key=lambda p: (not p.is_dir(), p.name.lower()),
                )
            except PermissionError:
                entries = []

            for entry in entries:
                if _should_exclude(entry.name):
                    continue
                child = self._read_node(entry, depth + 1, max_depth)
                children.append(child)

        return StructureNode(
            name=name,
            is_directory=True,
            children=tuple(children),
            depth=depth,
        )


# -----------------------------------------------------------------------------
# Configuration Section
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfigurationField:
    """
    A single configuration field with its metadata.
    """

    name: str
    field_type: str
    value: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class ConfigurationSection:
    """
    A documentation configuration section.
    """

    name: str
    description: str
    fields: tuple[ConfigurationField, ...] = ()


# -----------------------------------------------------------------------------
# Configuration Reader
# -----------------------------------------------------------------------------


class ConfigurationReader:
    """
    Reads the Engineering Toolkit configuration and produces
    documentation-friendly representations.
    """

    def __init__(self, config: Configuration | None = None) -> None:
        from Engineering.core.config import get_config

        self._config = config if config is not None else get_config()

    def sections(self) -> tuple[ConfigurationSection, ...]:
        """
        Return all configuration sections as documentation models.
        """

        sections: list[ConfigurationSection] = []
        sections.append(self._read_project_section())
        sections.append(self._read_engineering_section())
        sections.append(self._read_documentation_section())
        sections.append(self._read_logging_section())
        return tuple(sections)

    def _read_project_section(self) -> ConfigurationSection:
        """
        Read the project configuration section.
        """

        p = self._config.project
        return ConfigurationSection(
            name="Project",
            description="Project-level metadata and identity.",
            fields=(
                ConfigurationField("name", "str", p.name),
                ConfigurationField("short_name", "str", p.short_name),
                ConfigurationField("company", "str", p.company),
                ConfigurationField("version", "str", p.version),
                ConfigurationField("license", "str", p.license),
                ConfigurationField("python.minimum_version", "str", p.python.minimum_version),
            ),
        )

    def _read_engineering_section(self) -> ConfigurationSection:
        """
        Read the engineering configuration section.
        """

        e = self._config.engineering
        return ConfigurationSection(
            name="Engineering",
            description="Engineering Toolkit behavior settings.",
            fields=(
                ConfigurationField("strict_mode", "bool", str(e.strict_mode).lower()),
                ConfigurationField("diagnostics", "bool", str(e.diagnostics).lower()),
                ConfigurationField("cache.enabled", "bool", str(e.cache.enabled).lower()),
                ConfigurationField("validation.enabled", "bool", str(e.validation.enabled).lower()),
                ConfigurationField(
                    "paths.verify_on_startup",
                    "bool",
                    str(e.paths.verify_on_startup).lower(),
                ),
            ),
        )

    def _read_documentation_section(self) -> ConfigurationSection:
        """
        Read the documentation configuration section.
        """

        d = self._config.documentation
        return ConfigurationSection(
            name="Documentation",
            description="Documentation subsystem configuration.",
            fields=(
                ConfigurationField("enabled", "bool", str(d.enabled).lower()),
                ConfigurationField("output.root", "str", d.output.root),
                ConfigurationField("generate.readme", "bool", str(d.generate.readme).lower()),
                ConfigurationField("generate.api", "bool", str(d.generate.api).lower()),
                ConfigurationField(
                    "generate.architecture",
                    "bool",
                    str(d.generate.architecture).lower(),
                ),
                ConfigurationField("generate.adrs", "bool", str(d.generate.adrs).lower()),
                ConfigurationField(
                    "generate.project_status",
                    "bool",
                    str(d.generate.project_status).lower(),
                ),
                ConfigurationField("generate.changelog", "bool", str(d.generate.changelog).lower()),
                ConfigurationField("generate.index", "bool", str(d.generate.index).lower()),
                ConfigurationField("generate.manifests", "bool", str(d.generate.manifests).lower()),
            ),
        )

    def _read_logging_section(self) -> ConfigurationSection:
        """
        Read the logging configuration section.
        """

        lg = self._config.logging
        return ConfigurationSection(
            name="Logging",
            description="Logging subsystem configuration.",
            fields=(
                ConfigurationField("enabled", "bool", str(lg.enabled).lower()),
                ConfigurationField("level", "str", lg.level),
                ConfigurationField("console", "bool", str(lg.console).lower()),
                ConfigurationField("file", "bool", str(lg.file).lower()),
                ConfigurationField("directory", "str", lg.directory),
                ConfigurationField("filename", "str", lg.filename),
            ),
        )
