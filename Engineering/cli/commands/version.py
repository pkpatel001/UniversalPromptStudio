"""
Version command.
"""

from __future__ import annotations

from Engineering.cli.output.console import console
from Engineering.core.constants import ENGINEERING_NAME
from Engineering.core.version import VERSION


def version() -> None:
    """Display toolkit version."""
    console.print(f"{ENGINEERING_NAME} {VERSION}")