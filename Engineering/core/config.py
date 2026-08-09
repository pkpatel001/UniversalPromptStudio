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


def _validate_str(value: object, filename: str, key_path: str) -> str:
    """
    Validate that a configuration value is a string.

    Parameters
    ----------
    value
        Configuration value to validate.
    filename
        Configuration file name for error messages.
    key_path
        Dot-separated configuration path for error messages.

    Returns
    -------
    str
        The validated string value.

    Raises
    ------
    ConfigurationValidationError
        If the value is not a string.
    """

    if not isinstance(value, str):
        raise ConfigurationValidationError(
            f"Invalid configuration value at {key_path} in {filename}: "
            f"expected str, received {type(value).__name__}."
        )

    return value


def _validate_bool(value: object, filename: str, key_path: str) -> bool:
    """
    Validate that a configuration value is a boolean.

    Parameters
    ----------
    value
        Configuration value to validate.
    filename
        Configuration file name for error messages.
    key_path
        Dot-separated configuration path for error messages.

    Returns
    -------
    bool
        The validated boolean value.

    Raises
    ------
    ConfigurationValidationError
        If the value is not a boolean.
    """

    if not isinstance(value, bool):
        raise ConfigurationValidationError(
            f"Invalid configuration value at {key_path} in {filename}: "
            f"expected bool, received {type(value).__name__}."
        )

    return value


def _validate_mapping(
    value: object,
    filename: str,
    key_path: str,
    required_keys: tuple[str, ...],
) -> dict[str, object]:
    """
    Validate that a configuration value is a mapping with expected keys.

    Parameters
    ----------
    value
        Configuration value to validate.
    filename
        Configuration file name for error messages.
    key_path
        Dot-separated configuration path for error messages.
    required_keys
        Keys that must be present in the mapping.

    Returns
    -------
    dict[str, object]
        The validated mapping.

    Raises
    ------
    ConfigurationValidationError
        If the value is not a mapping, is missing required keys,
        or contains unknown keys.
    """

    if not isinstance(value, dict):
        raise ConfigurationValidationError(
            f"Invalid configuration value at {key_path} in {filename}: "
            f"expected mapping, received {type(value).__name__}."
        )

    missing = [key for key in required_keys if key not in value]

    if missing:
        raise ConfigurationValidationError(
            f"Missing required configuration key(s) at {key_path} in {filename}: "
            f"{', '.join(missing)}"
        )

    unknown = [key for key in value if key not in required_keys]

    if unknown:
        raise ConfigurationValidationError(
            f"Unknown configuration key(s) at {key_path} in {filename}: "
            f"{', '.join(unknown)}"
        )

    return value


def _load_config(
    path: Path,
    expected_root: str,
    required_keys: tuple[str, ...],
) -> dict[str, object]:
    """
    Load and validate a configuration file.

    This generic loader handles common configuration file validation:
    filename/root-key integrity, YAML parsing, root mapping validation,
    required-key presence, and unknown-key rejection.

    Parameters
    ----------
    path
        Path to the configuration file.
    expected_root
        Expected root YAML key (must match the filename stem).
    required_keys
        Keys that must be present in the root mapping.

    Returns
    -------
    dict[str, object]
        Validated root mapping.

    Raises
    ------
    ConfigurationFileNotFoundError
        If the file does not exist.
    ConfigurationValidationError
        If the file is structurally invalid.
    """

    if not path.is_file():
        raise ConfigurationFileNotFoundError(
            f"Configuration file not found: {path}"
        )

    if path.stem != expected_root:
        raise ConfigurationValidationError(
            f"Invalid configuration file {path.name}: "
            f"filename stem '{path.stem}' does not match expected root key '{expected_root}'."
        )

    data = read_yaml(path)

    root = data.get(expected_root)

    if root is None:
        raise ConfigurationValidationError(
            f"Invalid configuration file {path.name}: "
            f"expected root key '{expected_root}' not found."
        )

    if not isinstance(root, dict):
        raise ConfigurationValidationError(
            f"Invalid configuration file {path.name}: "
            f"expected root key '{expected_root}' to be a mapping, "
            f"received {type(root).__name__}."
        )

    missing = [key for key in required_keys if key not in root]

    if missing:
        raise ConfigurationValidationError(
            f"Missing required configuration key(s) in {path.name} "
            f"under '{expected_root}': {', '.join(missing)}"
        )

    unknown = [key for key in root if key not in required_keys]

    if unknown:
        raise ConfigurationValidationError(
            f"Unknown configuration key(s) in {path.name} "
            f"under '{expected_root}': {', '.join(unknown)}"
        )

    return root


# -----------------------------------------------------------------------------
# Configuration Loaders
# -----------------------------------------------------------------------------


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

    root = _load_config(
        path,
        "project",
        ("name", "short_name", "company", "version", "license", "python"),
    )

    python_data = _validate_mapping(
        root["python"],
        path.name,
        "project.python",
        ("minimum_version",),
    )

    return ProjectConfiguration(
        name=_validate_str(root["name"], path.name, "project.name"),
        short_name=_validate_str(root["short_name"], path.name, "project.short_name"),
        company=_validate_str(root["company"], path.name, "project.company"),
        version=_validate_str(root["version"], path.name, "project.version"),
        license=_validate_str(root["license"], path.name, "project.license"),
        python=PythonConfiguration(
            minimum_version=_validate_str(
                python_data["minimum_version"],
                path.name,
                "project.python.minimum_version",
            ),
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

    root = _load_config(
        path,
        "engineering",
        ("strict_mode", "diagnostics", "cache", "validation", "paths"),
    )

    cache_data = _validate_mapping(
        root["cache"],
        path.name,
        "engineering.cache",
        ("enabled",),
    )

    validation_data = _validate_mapping(
        root["validation"],
        path.name,
        "engineering.validation",
        ("enabled",),
    )

    paths_data = _validate_mapping(
        root["paths"],
        path.name,
        "engineering.paths",
        ("verify_on_startup",),
    )

    return EngineeringConfiguration(
        strict_mode=_validate_bool(root["strict_mode"], path.name, "engineering.strict_mode"),
        diagnostics=_validate_bool(root["diagnostics"], path.name, "engineering.diagnostics"),
        cache=CacheConfiguration(
            enabled=_validate_bool(cache_data["enabled"], path.name, "engineering.cache.enabled"),
        ),
        validation=ValidationConfiguration(
            enabled=_validate_bool(
                validation_data["enabled"],
                path.name,
                "engineering.validation.enabled",
            ),
        ),
        paths=EngineeringPathsConfiguration(
            verify_on_startup=_validate_bool(
                paths_data["verify_on_startup"],
                path.name,
                "engineering.paths.verify_on_startup",
            ),
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

    root = _load_config(
        path,
        "documentation",
        ("enabled", "output", "generate"),
    )

    output_data = _validate_mapping(
        root["output"],
        path.name,
        "documentation.output",
        ("root",),
    )

    generate_data = _validate_mapping(
        root["generate"],
        path.name,
        "documentation.generate",
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
        enabled=_validate_bool(root["enabled"], path.name, "documentation.enabled"),
        output=DocumentationOutputConfiguration(
            root=_validate_str(output_data["root"], path.name, "documentation.output.root"),
        ),
        generate=DocumentationGenerateConfiguration(
            readme=_validate_bool(
                generate_data["readme"],
                path.name,
                "documentation.generate.readme",
            ),
            api=_validate_bool(generate_data["api"], path.name, "documentation.generate.api"),
            architecture=_validate_bool(
                generate_data["architecture"],
                path.name,
                "documentation.generate.architecture",
            ),
            adrs=_validate_bool(generate_data["adrs"], path.name, "documentation.generate.adrs"),
            project_status=_validate_bool(
                generate_data["project_status"],
                path.name,
                "documentation.generate.project_status",
            ),
            changelog=_validate_bool(
                generate_data["changelog"],
                path.name,
                "documentation.generate.changelog",
            ),
            index=_validate_bool(generate_data["index"], path.name, "documentation.generate.index"),
            manifests=_validate_bool(
                generate_data["manifests"],
                path.name,
                "documentation.generate.manifests",
            ),
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

    root = _load_config(
        path,
        "logging",
        ("enabled", "level", "console", "file", "directory", "filename"),
    )

    return LoggingConfiguration(
        enabled=_validate_bool(root["enabled"], path.name, "logging.enabled"),
        level=_validate_str(root["level"], path.name, "logging.level"),
        console=_validate_bool(root["console"], path.name, "logging.console"),
        file=_validate_bool(root["file"], path.name, "logging.file"),
        directory=_validate_str(root["directory"], path.name, "logging.directory"),
        filename=_validate_str(root["filename"], path.name, "logging.filename"),
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
