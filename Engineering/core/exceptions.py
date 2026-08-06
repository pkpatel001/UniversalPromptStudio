"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Exception Hierarchy

This module defines the canonical exception hierarchy used throughout the
Engineering Toolkit.

All toolkit-specific exceptions should derive from EngineeringError.

===============================================================================
"""

from __future__ import annotations

__all__ = [
    "EngineeringError",
    "FilesystemError",
    "FileReadError",
    "FileWriteError",
    "ConfigurationError",
    "ConfigurationFileNotFoundError",
    "ConfigurationValidationError",
    "ProjectRootNotFoundError",
    "DocumentationError",
    "DocumentationGenerationError",
    "BuildError",
]


# -----------------------------------------------------------------------------
# Base Exceptions
# -----------------------------------------------------------------------------


class EngineeringError(Exception):
    """
    Base exception for the Engineering Toolkit.

    All custom Engineering Toolkit exceptions derive from this class.
    """


# -----------------------------------------------------------------------------
# Filesystem
# -----------------------------------------------------------------------------


class FilesystemError(EngineeringError):
    """
    Base exception for filesystem-related errors.
    """


class FileReadError(FilesystemError):
    """
    Raised when a file cannot be read.
    """


class FileWriteError(FilesystemError):
    """
    Raised when a file cannot be written.
    """


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


class ConfigurationError(EngineeringError):
    """
    Base exception for configuration-related errors.
    """


class ConfigurationFileNotFoundError(ConfigurationError):
    """
    Raised when a required configuration file cannot be found.
    """


class ConfigurationValidationError(ConfigurationError):
    """
    Raised when configuration validation fails.
    """


# -----------------------------------------------------------------------------
# Project
# -----------------------------------------------------------------------------


class ProjectRootNotFoundError(EngineeringError):
    """
    Raised when the Universal Prompt Studio project root cannot be located.
    """


# -----------------------------------------------------------------------------
# Documentation
# -----------------------------------------------------------------------------


class DocumentationError(EngineeringError):
    """
    Base exception for documentation-related errors.
    """


class DocumentationGenerationError(DocumentationError):
    """
    Raised when documentation generation fails.
    """


# -----------------------------------------------------------------------------
# Build System
# -----------------------------------------------------------------------------


class BuildError(EngineeringError):
    """
    Base exception for build and release operations.
    """