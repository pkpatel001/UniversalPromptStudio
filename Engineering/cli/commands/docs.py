"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation CLI Commands

This module implements the documentation generation and validation CLI.

Commands:
  docs generate  — Generate documentation from project sources
  docs validate  — Validate generated documentation

Public API
----------
python -m Engineering docs generate
python -m Engineering docs validate

===============================================================================
"""

from __future__ import annotations

import typer

from Engineering.cli.errors import (
    EXIT_CODE_CONFIGURATION,
    EXIT_CODE_INTERNAL,
    EXIT_CODE_SUCCESS,
    EXIT_CODE_VALIDATION_FAILURE,
)
from Engineering.cli.output.console import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(help="Documentation generation and validation")


@app.callback(invoke_without_command=True)
def docs_main(ctx: typer.Context) -> None:
    """Documentation subsystem."""
    if ctx.invoked_subcommand is None:
        print_info("Use 'docs generate' or 'docs validate'.")


@app.command(name="generate")
def docs_generate() -> None:
    """
    Generate documentation from project sources.

    Reads project configuration, repository structure, and Python source
    metadata to produce deterministic Markdown documentation in the
    configured output directory.
    """

    print_info("Starting documentation generation...")

    try:
        from Engineering.core.config import get_config
        from Engineering.core.exceptions import (
            ConfigurationError,
            DocumentationError,
            DocumentationGenerationError,
        )
        from Engineering.core.paths import get_paths
        from Engineering.Documentation.generator import DocumentationGenerator

        config = get_config()
        paths = get_paths()

        if not config.documentation.enabled:
            print_warning("Documentation generation is disabled in configuration.")
            raise typer.Exit(code=EXIT_CODE_SUCCESS)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        if report.generated:
            console.print()
            for doc in report.generated:
                print_success(f"{doc.title} ({doc.path})")
            console.print()

        if report.skipped:
            for name in report.skipped:
                print_warning(f"Skipped: {name}")
            console.print()

        if report.failed:
            for fail in report.failed:
                print_error(f"Failed: {fail.identifier} — {fail.reason}")
            console.print()

        print_success(report.summary)
        console.print(f"Output: {report.output_root}")
        console.print()

        if not report.success:
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)

        raise typer.Exit(code=EXIT_CODE_SUCCESS)

    except DocumentationError as exc:
        print_error(f"Documentation generation failed: {exc}")
        raise typer.Exit(code=EXIT_CODE_INTERNAL)

    except ConfigurationError as exc:
        print_error(f"Configuration error: {exc}")
        raise typer.Exit(code=EXIT_CODE_CONFIGURATION)

    except typer.Exit:
        raise

    except Exception as exc:
        print_error(f"Unexpected error: {exc}")
        raise typer.Exit(code=EXIT_CODE_INTERNAL)


@app.command(name="validate")
def docs_validate() -> None:
    """
    Validate generated documentation.

    Checks that all expected documents exist and contain the
    auto-generated marker header.
    """

    from pathlib import Path

    from Engineering.core.config import get_config
    from Engineering.core.exceptions import ConfigurationError
    from Engineering.core.filesystem import exists, is_file, read_text
    from Engineering.core.paths import get_paths

    AUTO_GENERATED_MARKER = "AUTO-GENERATED FILE"

    try:
        config = get_config()
        paths = get_paths()

        if not config.documentation.enabled:
            print_warning("Documentation subsystem is disabled in configuration.")
            raise typer.Exit(code=EXIT_CODE_SUCCESS)

        output_root = (paths.root / config.documentation.output.root).resolve()

        if not exists(output_root):
            print_warning(f"Output directory does not exist: {output_root}")
            print_warning("Run 'docs generate' first.")
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)

        console.print()
        print_info("Validating generated documentation...")
        console.print()

        errors: list[str] = []

        expected_files: list[str] = []
        gen = config.documentation.generate

        if gen.readme:
            expected_files.append("README.md")
        if gen.architecture:
            expected_files.append("architecture.md")
        if gen.project_status:
            expected_files.append("project-status.md")
        if gen.index:
            expected_files.append("index.md")
        if gen.api:
            expected_files.append("api/README.md")
        expected_files.append("adrs.md")

        for rel_path in expected_files:
            full_path = output_root / rel_path
            if not is_file(full_path):
                errors.append(f"Missing expected document: {rel_path}")
                continue

            try:
                content = read_text(full_path)
                if AUTO_GENERATED_MARKER not in content:
                    errors.append(
                        f"Missing auto-generated marker: {rel_path}"
                    )
            except Exception as exc:
                errors.append(f"Failed to read: {rel_path} ({exc})")

        if errors:
            for error in errors:
                print_error(error)
            console.print()
            print_error(
                f"Documentation validation failed: {len(errors)} error(s)."
            )
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)

        print_success("Generated documentation is valid.")
        console.print()

        raise typer.Exit(code=EXIT_CODE_SUCCESS)

    except ConfigurationError as exc:
        print_error(f"Configuration error: {exc}")
        raise typer.Exit(code=EXIT_CODE_CONFIGURATION)

    except typer.Exit:
        raise

    except Exception as exc:
        print_error(f"Unexpected error: {exc}")
        raise typer.Exit(code=EXIT_CODE_INTERNAL)
