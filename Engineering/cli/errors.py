"""
CLI error types and exit code mapping.
"""

from __future__ import annotations

import sys
import traceback
from typing import NoReturn

from rich.console import Console

from Engineering.core.exceptions import (
    ConfigurationError,
    EngineeringError,
    ProjectRootNotFoundError,
)

console = Console()


class CLIConfigurationError(Exception):
    """Raised when configuration loading fails (maps to exit 3)."""


class CLIProjectError(Exception):
    """Raised when project/environment issues occur (maps to exit 4)."""


EXIT_CODE_SUCCESS = 0
EXIT_CODE_VALIDATION_FAILURE = 1
EXIT_CODE_CLI_USAGE = 2
EXIT_CODE_CONFIGURATION = 3
EXIT_CODE_PROJECT = 4
EXIT_CODE_INTERNAL = 5


def exit_with_code(code: int, message: str | None = None) -> NoReturn:
    """Exit the CLI with a specific code and optional message."""
    if message:
        if code == EXIT_CODE_SUCCESS:
            console.print(message)
        else:
            console.print(f"[red]{message}[/red]")
    sys.exit(code)


def translate_exception(exc: BaseException, verbose: bool = False) -> int:
    """
    Translate an exception into a CLI exit code.
    """
    if isinstance(exc, SystemExit):
        return exc.code if isinstance(exc.code, int) else EXIT_CODE_SUCCESS

    if isinstance(exc, CLIConfigurationError) or isinstance(exc, ConfigurationError):
        console.print(f"[red]Configuration error:[/red] {exc}")
        return EXIT_CODE_CONFIGURATION

    if isinstance(exc, CLIProjectError) or isinstance(exc, ProjectRootNotFoundError):
        console.print(f"[red]Project error:[/red] {exc}")
        return EXIT_CODE_PROJECT

    if isinstance(exc, EngineeringError):
        console.print(f"[red]Engineering error:[/red] {exc}")
        return EXIT_CODE_INTERNAL

    console.print(f"[red]Unexpected error:[/red] {exc}")
    if verbose:
        console.print(traceback.format_exc())
    return EXIT_CODE_INTERNAL