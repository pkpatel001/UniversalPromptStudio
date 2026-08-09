"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Configuration System

This module provides the canonical, immutable configuration for the
Engineering Toolkit. All configuration values are loaded from YAML files
and exposed as frozen dataclasses.

No raw dictionaries are exposed outside this module.

Public API
----------
from Engineering.core.config import get_config

config = get_config()
config.project.name
config.documentation.generate.api
config.logging.level

===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .constants import (
    DOCUMENTATION_CONFIG_FILENAME,
    ENGINEERING_CONFIG_FILENAME,
    LOGGING_CONFIG_FILENAME,
    PROJECT_CONFIG_FILENAME,
)
from .exceptions import (
    ConfigurationError,
    ConfigurationFileNotFoundError,
    ConfigurationValidationError,
)
from .filesystem import read_yaml
from .paths import get_paths

__all__ = [
    "Configuration",
    "ProjectConfiguration",
    "EngineeringConfiguration",
    "DocumentationConfiguration",
    "LoggingConfiguration",
    "PythonConfiguration",
    "CacheConfiguration",
    "ValidationConfiguration",
    "EngineeringPathsConfiguration",
    "DocumentationOutputConfiguration",
    "DocumentationGenerateConfiguration",
    "get_config",
]


# -----------------------------------------------------------------------------
# Configuration Dataclasses
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PythonConfiguration:
    """
    Python runtime requirements.
    """

    minimum_version: str


@dataclass(frozen=True, slots=True)
class ProjectConfiguration:
    """
    Project-level metadata.
    """

    name: str
    short_name: str
    company: str
    version: str
    license: str
    python: PythonConfiguration


@dataclass(frozen=True, slots=True)
class CacheConfiguration:
    """
    Engineering Toolkit cache settings.
    """

    enabled: bool


@dataclass(frozen=True, slots=True)
class ValidationConfiguration:
    """
    Engineering Toolkit validation settings.
    """

    enabled: bool


@dataclass(frozen=True, slots=True)
class EngineeringPathsConfiguration:
    """
    Engineering Toolkit path behavior.
    """

    verify_on_startup: bool


@dataclass(frozen=True, slots=True)
class EngineeringConfiguration:
    """
    Engineering Toolkit behavior settings.
    """

    strict_mode: bool
    diagnostics: bool
    cache: CacheConfiguration
    validation: ValidationConfiguration
    paths: EngineeringPathsConfiguration


@dataclass(frozen=True, slots=True)
class DocumentationOutputConfiguration:
    """
    Documentation output settings.
    """

    root: str


@dataclass(frozen=True, slots=True)
class DocumentationGenerateConfiguration:
    """
    Documentation generation toggles.
    """

    readme: bool
    api: bool
    architecture: bool
    adrs: bool
    project_status: bool
    changelog: bool
    index: bool
    manifests: bool


@dataclass(frozen=True, slots=True)
class DocumentationConfiguration:
    """
    Documentation subsystem configuration.
    """

    enabled: bool
    output: DocumentationOutputConfiguration
    generate: DocumentationGenerateConfiguration


@dataclass(frozen=True, slots=True)
class LoggingConfiguration:
    """
    Logging subsystem configuration.
    """

    enabled: bool
    level: str
    console: bool
    file: bool
    directory: str
    filename: str


@dataclass(frozen=True, slots=True)
class Configuration:
    """
    Top-level Engineering Toolkit configuration.

    Contains all configuration sections loaded from YAML files.
    """

    project: ProjectConfiguration
    engineering: EngineeringConfiguration
    documentation: DocumentationConfiguration
    logging: LoggingConfiguration


# -----------------------------------------------------------------------------
# Validation Helpers
# -----------------------------------------------------------------------------


def _require_keys(data: dict[str, object], keys: tuple[str, ...]) -> None:
    """
    Ensure that all required keys exist in a mapping.

    Parameters
    ----------
    data
        Mapping to validate.
    keys
        Required keys.

    Raises
    ------
    ConfigurationValidationError
        If any required key is missing.
    """

    missing = [key for key in keys if key not in data]

    if missing:
        raise ConfigurationValidationError(
            f"Missing required configuration keys: {', '.join(missing)}"
        )


def _load_project_config(path: Path) -> ProjectConfiguration:
    """
    Load and validate project configuration.

    Parameters
    ----------
    path
        Path to project.yaml.

    Returns
    -------
    ProjectConfiguration
    """

    data = read_yaml(path)

    root = data.get("project")
    if not isinstance(root, dict):
        raise ConfigurationValidationError(
            "Expected 'project' to be a mapping in project.yaml"
        )

    _require_keys(root, ("name", "short_name", "company", "version", "license", "python"))

    python_data = root["python"]
    if not isinstance(python_data, dict):
        raise ConfigurationValidationError(
            "Expected 'project.python' to be a mapping in project.yaml"
        )

    _require_keys(python_data, ("minimum_version",))

    return ProjectConfiguration(
        name=str(root["name"]),
        short_name=str(root["short_name"]),
        company=str(root["company"]),
        version=str(root["version"]),
        license=str(root["license"]),
        python=PythonConfiguration(
            minimum_version=str(python_data["minimum_version"])
        ),
    )


def _load_engineering_config(path: Path) -> EngineeringConfiguration:
    """
    Load and validate engineering configuration.

    Parameters
    ----------
    path
        Path to engineering.yaml.

    Returns
    -------
    EngineeringConfiguration
    """

    data = read_yaml(path)

    root = data.get("engineering")
    if not isinstance(root, dict):
        raise ConfigurationValidationError(
            "Expected 'engineering' to be a mapping in engineering.yaml"
        )

    _require_keys(root, ("strict_mode", "diagnostics", "cache", "validation", "paths"))

    cache_data = root["cache"]
    if not isinstance(cache_data, dict):
        raise ConfigurationValidationError(
            "Expected 'engineering.cache' to be a mapping in engineering.yaml"
        )

    _require_keys(cache_data, ("enabled",))

    validation_data = root["validation"]
    if not isinstance(validation_data, dict):
        raise ConfigurationValidationError(
            "Expected 'engineering.validation' to be a mapping in engineering.yaml"
        )

    _require_keys(validation_data, ("enabled",))

    paths_data = root["paths"]
    if not isinstance(paths_data, dict):
        raise ConfigurationValidationError(
            "Expected 'engineering.paths' to be a mapping in engineering.yaml"
        )

    _require_keys(paths_data, ("verify_on_startup",))

    return EngineeringConfiguration(
        strict_mode=bool(root["strict_mode"]),
        diagnostics=bool(root["diagnostics"]),
        cache=CacheConfiguration(enabled=bool(cache_data["enabled"])),
        validation=ValidationConfiguration(enabled=bool(validation_data["enabled"])),
        paths=EngineeringPathsConfiguration(
            verify_on_startup=bool(paths_data["verify_on_startup"])
        ),
    )


def _load_documentation_config(path: Path) -> DocumentationConfiguration:
    """
    Load and validate documentation configuration.

    Parameters
    ----------
    path
        Path to documentation.yaml.

    Returns
    -------
    DocumentationConfiguration
    """

    data = read_yaml(path)

    root = data.get("documentation")
    if not isinstance(root, dict):
        raise ConfigurationValidationError(
            "Expected 'documentation' to be a mapping in documentation.yaml"
        )

    _require_keys(root, ("enabled", "output", "generate"))

    output_data = root["output"]
    if not isinstance(output_data, dict):
        raise ConfigurationValidationError(
            "Expected 'documentation.output' to be a mapping in documentation.yaml"
        )

    _require_keys(output_data, ("root",))

    generate_data = root["generate"]
    if not isinstance(generate_data, dict):
        raise ConfigurationValidationError(
            "Expected 'documentation.generate' to be a mapping in documentation.yaml"
        )

    _require_keys(
        generate_data,
        (
            "readme",
            "api",
            "architecture",
            "adrs",
            "project_status",
            "changelog",
            "index",
            "manifests",
        ),
    )

    return DocumentationConfiguration(
        enabled=bool(root["enabled"]),
        output=DocumentationOutputConfiguration(root=str(output_data["root"])),
        generate=DocumentationGenerateConfiguration(
            readme=bool(generate_data["readme"]),
            api=bool(generate_data["api"]),
            architecture=bool(generate_data["architecture"]),
            adrs=bool(generate_data["adrs"]),
            project_status=bool(generate_data["project_status"]),
            changelog=bool(generate_data["changelog"]),
            index=bool(generate_data["index"]),
            manifests=bool(generate_data["manifests"]),
        ),
    )


def _load_logging_config(path: Path) -> LoggingConfiguration:
    """
    Load and validate logging configuration.

    Parameters
    ----------
    path
        Path to logging.yaml.

    Returns
    -------
    LoggingConfiguration
    """

    data = read_yaml(path)

    root = data.get("logging")
    if not isinstance(root, dict):
        raise ConfigurationValidationError(
            "Expected 'logging' to be a mapping in logging.yaml"
        )

    _require_keys(root, ("enabled", "level", "console", "file", "directory", "filename"))

    return LoggingConfiguration(
        enabled=bool(root["enabled"]),
        level=str(root["level"]),
        console=bool(root["console"]),
        file=bool(root["file"]),
        directory=str(root["directory"]),
        filename=str(root["filename"]),
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_config() -> Configuration:
    """
    Load and return the Engineering Toolkit configuration.

    Configuration is loaded once and cached for the lifetime of the process.

    Returns
    -------
    Configuration
        Immutable configuration instance.

    Raises
    ------
    ConfigurationFileNotFoundError
        If a required configuration file is missing.
    ConfigurationValidationError
        If a configuration file is structurally invalid.
    """

    paths = get_paths()
    config_dir = paths.config

    if not config_dir.is_dir():
        raise ConfigurationFileNotFoundError(
            f"Configuration directory not found: {config_dir}"
        )

    project_path = config_dir / PROJECT_CONFIG_FILENAME
    engineering_path = config_dir / ENGINEERING_CONFIG_FILENAME
    documentation_path = config_dir / DOCUMENTATION_CONFIG_FILENAME
    logging_path = config_dir / LOGGING_CONFIG_FILENAME

    missing_files = [
        str(path)
        for path in (
            project_path,
            engineering_path,
            documentation_path,
            logging_path,
        )
        if not path.is_file()
    ]

    if missing_files:
        raise ConfigurationFileNotFoundError(
            f"Required configuration files not found: {', '.join(missing_files)}"
        )

    try:
        project_config = _load_project_config(project_path)
        engineering_config = _load_engineering_config(engineering_path)
        documentation_config = _load_documentation_config(documentation_path)
        logging_config = _load_logging_config(logging_path)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(
            "Unexpected error while loading configuration."
        ) from exc

    return Configuration(
        project=project_config,
        engineering=engineering_config,
        documentation=documentation_config,
        logging=logging_config,
    )
