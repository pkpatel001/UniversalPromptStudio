"""
Configuration command.
"""

from __future__ import annotations

import typer

from Engineering.cli.errors import EXIT_CODE_CONFIGURATION
from Engineering.cli.output.console import console
from Engineering.core.config import get_config


def config() -> None:
    """
    Display configuration information.
    """
    try:
        cfg = get_config()
    except Exception as exc:
        raise typer.Exit(code=EXIT_CODE_CONFIGURATION) from exc

    console.print("[bold]Project[/bold]")
    console.print(f"  Name: {cfg.project.name}")
    console.print(f"  Short Name: {cfg.project.short_name}")
    console.print(f"  Company: {cfg.project.company}")
    console.print(f"  Version: {cfg.project.version}")
    console.print(f"  License: {cfg.project.license}")
    console.print(f"  Python: >={cfg.project.python.minimum_version}")
    console.print()

    console.print("[bold]Engineering[/bold]")
    console.print(f"  Strict Mode: {cfg.engineering.strict_mode}")
    console.print(f"  Validation: {cfg.engineering.validation.enabled}")
    console.print(f"  Cache: {cfg.engineering.cache.enabled}")
    console.print()

    console.print("[bold]Documentation[/bold]")
    console.print(f"  Enabled: {cfg.documentation.enabled}")
    console.print()