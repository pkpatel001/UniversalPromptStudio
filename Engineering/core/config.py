"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Configuration Infrastructure

This module provides the generic configuration loading infrastructure for the
Engineering Toolkit.

The implementation is intentionally schema-agnostic. Rather than defining
application-specific configuration models, this module provides reusable
utilities for loading immutable dataclass-based configuration objects from
YAML files.

Features
--------
* Generic YAML → dataclass deserialization
* Recursive dataclass construction
* Strong runtime validation
* Immutable configuration objects
* Thread-safe configuration cache
* Automatic project root integration
* Helpful exception hierarchy
* Type-safe public API

The module depends only upon the Engineering core infrastructure and therefore
remains reusable across every subsystem of the Universal Prompt Studio.

Notes
-----
Configuration schemas themselves should live elsewhere (for example,
``Engineering/config``). This module should never contain application-specific
configuration dataclasses.

Examples
--------
>>> from pathlib import Path
>>> from Engineering.config.app import AppConfig
>>> cfg = load_config(AppConfig, Path("config/app.yaml"))

===============================================================================
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING
from dataclasses import Field
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path
from threading import RLock
from typing import Any
from typing import Final
from typing import TypeAlias
from typing import TypeVar
from typing import Union
from typing import get_args
from typing import get_origin
from typing import get_type_hints
import logging

from Engineering.core.constants import DEFAULT_ENCODING
from Engineering.core.exceptions import (
    ConfigurationError,
    ConfigurationValidationError,
)
from Engineering.core.filesystem import read_yaml
from Engineering.core.paths import get_paths

__all__: list[str] = [
    "ConfigurationError",
    "ConfigurationFileError",
    "ConfigurationValidationError",
    "ConfigurationTypeError",
    "load_config",
    "load_config_from_file",
    "load_config_from_mapping",
    "get_config",
    "reload_config",
    "clear_config_cache",
]

###############################################################################
# Logging
###############################################################################

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

###############################################################################
# Generic typing
###############################################################################

ConfigT = TypeVar("ConfigT")

DataclassType = TypeVar("DataclassType")

PathLike: TypeAlias = str | Path

MappingType: TypeAlias = Mapping[str, Any]

CacheKey: TypeAlias = tuple[type[Any], Path]

###############################################################################
# Internal module state
###############################################################################

_CONFIGURATION_CACHE: dict[CacheKey, Any] = {}

_CACHE_LOCK: Final[RLock] = RLock()

###############################################################################
# Supported scalar types
###############################################################################

_SUPPORTED_SCALAR_TYPES: Final[frozenset[type[Any]]] = frozenset(
    {
        bool,
        int,
        float,
        str,
        Path,
    }
)

###############################################################################
# Default configuration location
###############################################################################

_DEFAULT_CONFIG_DIRECTORY: Final[Path] = get_paths().config

###############################################################################
# Helper utilities
###############################################################################


def _normalize_path(path: PathLike) -> Path:
    """
    Normalize a filesystem path.

    Parameters
    ----------
    path
        Path supplied by the caller.

    Returns
    -------
    Path
        Fully resolved absolute path.

    Notes
    -----
    Relative paths are interpreted relative to the current working directory
    before resolution.
    """
    return Path(path).expanduser().resolve()


def _cache_key(
    configuration_type: type[Any],
    configuration_path: PathLike,
) -> CacheKey:
    """
    Construct the cache key used internally.

    Parameters
    ----------
    configuration_type
        Requested configuration class.

    configuration_path
        YAML configuration file.

    Returns
    -------
    CacheKey
        Immutable cache identifier.
    """
    return (
        configuration_type,
        _normalize_path(configuration_path),
    )


def _is_optional_type(annotation: Any) -> bool:
    """
    Determine whether a type annotation represents an Optional value.

    Parameters
    ----------
    annotation
        Type annotation.

    Returns
    -------
    bool
        True if Optional[...] or X | None.
    """
    origin = get_origin(annotation)

    if origin is Union:
        return type(None) in get_args(annotation)

    return False

    
def _strip_optional_type(annotation: Any) -> Any:
    """
    Remove Optional from a type annotation.

    Parameters
    ----------
    annotation
        Type annotation.

    Returns
    -------
    Any
        Underlying annotation with ``None`` removed.
    """
    if not _is_optional_type(annotation):
        return annotation

    return next(
        candidate
        for candidate in get_args(annotation)
        if candidate is not type(None)
    )


def _is_dataclass_type(annotation: Any) -> bool:
    """
    Determine whether an annotation represents a dataclass type.

    Parameters
    ----------
    annotation
        Annotation to inspect.

    Returns
    -------
    bool
        True if the annotation is a dataclass type.
    """
    annotation = _strip_optional_type(annotation)

    try:
        return is_dataclass(annotation)
    except TypeError:
        return False


def _is_mapping_type(annotation: Any) -> bool:
    """
    Determine whether an annotation represents a mapping.

    Parameters
    ----------
    annotation
        Type annotation.

    Returns
    -------
    bool
        True if the annotation is mapping-like.
    """
    annotation = _strip_optional_type(annotation)

    origin = get_origin(annotation)

    if origin is None:
        return False

    return issubclass(origin, Mapping)


def _is_sequence_type(annotation: Any) -> bool:
    """
    Determine whether an annotation represents a sequence.

    Strings and bytes are intentionally excluded.

    Parameters
    ----------
    annotation
        Type annotation.

    Returns
    -------
    bool
        True if the annotation represents a supported sequence.
    """
    annotation = _strip_optional_type(annotation)

    origin = get_origin(annotation)

    return origin in (
        list,
        tuple,
        set,
        frozenset,
    )


def _is_scalar_type(annotation: Any) -> bool:
    """
    Determine whether an annotation represents a supported scalar.

    Parameters
    ----------
    annotation
        Annotation to inspect.

    Returns
    -------
    bool
        True if supported.
    """
    annotation = _strip_optional_type(annotation)

    return annotation in _SUPPORTED_SCALAR_TYPES


###############################################################################
# Configuration-specific exceptions
###############################################################################


class ConfigurationTypeError(ConfigurationValidationError):
    """
    Raised when a configuration value cannot be converted to
    its declared Python type.
    """

###############################################################################
# Validation helpers
###############################################################################


def _field_name(field: Field[Any]) -> str:
    """
    Return a readable field name.

    Parameters
    ----------
    field
        Dataclass field.

    Returns
    -------
    str
        Human-readable field name.
    """
    return field.name.replace("_", " ")


def _raise_missing_field(
    field: Field[Any],
    dataclass_type: type[Any],
) -> None:
    """
    Raise an exception for a missing required field.

    Parameters
    ----------
    field
        Missing dataclass field.

    dataclass_type
        Owning dataclass.

    Raises
    ------
    ConfigurationValidationError
    """
    raise ConfigurationValidationError(
        f"Required field "
        f"'{field.name}' "
        f"is missing while loading "
        f"{dataclass_type.__name__}."
    )


def _raise_invalid_type(
    *,
    field_name: str,
    expected: Any,
    actual: Any,
) -> None:
    """
    Raise a strongly formatted type mismatch exception.

    Parameters
    ----------
    field_name
        Field being processed.

    expected
        Expected Python type.

    actual
        Actual value.
    """
    expected_name = getattr(
        expected,
        "__name__",
        str(expected),
    )

    actual_name = type(actual).__name__

    raise ConfigurationTypeError(
        f"Field '{field_name}' expected "
        f"{expected_name} "
        f"but received "
        f"{actual_name}."
    )


def _has_default(field: Field[Any]) -> bool:
    """
    Determine whether a dataclass field defines a default.

    Parameters
    ----------
    field
        Dataclass field.

    Returns
    -------
    bool
        True if a default value or factory exists.
    """
    return (
        field.default is not MISSING
        or field.default_factory is not MISSING
    )


def _is_required(field: Field[Any]) -> bool:
    """
    Determine whether a dataclass field is required.

    Parameters
    ----------
    field
        Dataclass field.

    Returns
    -------
    bool
        True if the field has no default value.
    """
    return not _has_default(field)
    
###############################################################################
# Generic conversion helpers
###############################################################################


def _coerce_scalar(
    value: Any,
    annotation: type[Any],
    *,
    field_name: str,
) -> Any:
    """
    Convert a scalar value to the requested Python type.

    Parameters
    ----------
    value
        Source value.

    annotation
        Target scalar type.

    field_name
        Name of the configuration field.

    Returns
    -------
    Any
        Converted scalar value.

    Raises
    ------
    ConfigurationTypeError
        If the value cannot be converted.
    """
    if isinstance(value, annotation):
        return value

    try:
        if annotation is Path:
            return Path(value)

        return annotation(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationTypeError(
            f"Field '{field_name}' cannot be converted "
            f"to {annotation.__name__}."
        ) from exc


def _convert_sequence(
    value: Any,
    annotation: Any,
    *,
    field_name: str,
) -> Any:
    """
    Convert a sequence to the requested container type.

    Parameters
    ----------
    value
        Source sequence.

    annotation
        Target annotation.

    field_name
        Name of the configuration field.

    Returns
    -------
    Any
        Converted sequence.
    """
    if not isinstance(value, (list, tuple, set, frozenset)):
        _raise_invalid_type(
            field_name=field_name,
            expected=annotation,
            actual=value,
        )

    origin = get_origin(annotation)
    arguments = get_args(annotation)

    element_type = Any

    if arguments:
        element_type = arguments[0]

    converted = [
        _convert_value(
            item,
            element_type,
            field_name=field_name,
        )
        for item in value
    ]

    if origin is tuple:
        return tuple(converted)

    if origin is set:
        return set(converted)

    if origin is frozenset:
        return frozenset(converted)

    return list(converted)


def _convert_mapping(
    value: Any,
    annotation: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    """
    Convert a mapping.

    Parameters
    ----------
    value
        Source mapping.

    annotation
        Target annotation.

    field_name
        Name of the configuration field.

    Returns
    -------
    Mapping[str, Any]
        Converted mapping.
    """
    if not isinstance(value, Mapping):
        _raise_invalid_type(
            field_name=field_name,
            expected=annotation,
            actual=value,
        )

    arguments = get_args(annotation)

    key_type: Any = str
    value_type: Any = Any

    if len(arguments) == 2:
        key_type, value_type = arguments

    converted: dict[Any, Any] = {}

    for key, item in value.items():
        converted_key = _convert_value(
            key,
            key_type,
            field_name=field_name,
        )

        converted_value = _convert_value(
            item,
            value_type,
            field_name=field_name,
        )

        converted[converted_key] = converted_value

    return converted


def _convert_value(
    value: Any,
    annotation: Any,
    *,
    field_name: str,
) -> Any:
    """
    Convert a Python object to the requested annotation.

    Parameters
    ----------
    value
        Source value.

    annotation
        Target annotation.

    field_name
        Name of the configuration field.

    Returns
    -------
    Any
        Converted value.
    """
    annotation = _strip_optional_type(annotation)

    if value is None:
        return None

    if annotation is Any:
        return value

    if _is_scalar_type(annotation):
        return _coerce_scalar(
            value,
            annotation,
            field_name=field_name,
        )

    if _is_sequence_type(annotation):
        return _convert_sequence(
            value,
            annotation,
            field_name=field_name,
        )

    if _is_mapping_type(annotation):
        return _convert_mapping(
            value,
            annotation,
            field_name=field_name,
        )

    if _is_dataclass_type(annotation):
        if not isinstance(value, Mapping):
            _raise_invalid_type(
                field_name=field_name,
                expected=annotation,
                actual=value,
            )

        return _deserialize_dataclass(
            annotation,
            value,
        )

    return value