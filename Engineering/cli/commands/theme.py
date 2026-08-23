"""Read-only CLI adapter for E-015 theme metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ThemeError
from Engineering.ThemeSystem import (
    ThemeAppearance,
    ThemeCatalog,
    ThemeDiscoveryRoot,
    ThemeManifestReader,
    ThemeService,
    ThemeValidationReport,
)

app = typer.Typer(help="Inspect declarative theme metadata without applying styles")


@app.callback(invoke_without_command=True)
def theme_main(ctx: typer.Context) -> None:
    """Inspect theme SDK metadata."""

    if ctx.invoked_subcommand is None:
        console.print(
            "Run 'python -m Engineering theme inspect MANIFEST' "
            "to validate declarative theme metadata."
        )


@app.command(name="inspect")
def theme_inspect(manifest: Path) -> None:
    """Validate and display one exact theme manifest."""

    try:
        parsed = ThemeManifestReader().read(manifest)
    except ThemeError as exc:
        console.print(f"FAILED theme.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    metadata = parsed.metadata
    console.print(f"Theme: {metadata.theme_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Default appearance: {parsed.default_appearance.value}")
    console.print("Appearances: " + ", ".join(item.appearance.value for item in parsed.palettes))
    console.print(f"Description: {metadata.description}")
    console.print("Theme assets loaded: no")
    console.print("Styles applied: no")
    console.print("Code executed: no")


def _roots(values: list[Path] | None) -> tuple[ThemeDiscoveryRoot, ...]:
    if not values:
        raise ThemeError("Theme catalog commands require at least one explicit --root.")
    return tuple(
        ThemeDiscoveryRoot(f"explicit-{index:04d}", path)
        for index, path in enumerate(values, start=1)
    )


def _validate(roots: tuple[ThemeDiscoveryRoot, ...]) -> ThemeValidationReport:
    try:
        return ThemeService().validate_roots(roots)
    except ThemeError as exc:
        console.print(f"FAILED theme.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc


def _print_report(report: ThemeValidationReport) -> None:
    for record in report.records:
        metadata = record.manifest.metadata
        appearances = ",".join(item.appearance.value for item in record.manifest.palettes)
        console.print(
            f"VALID {record.theme_id} version={record.version} "
            f"sdk={metadata.sdk_version.api_level} appearances={appearances} "
            f"root={record.root_id} path={record.relative_path}"
        )
    for issue in report.issues:
        console.print(
            f"FAILED {issue.code} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(report.summary)


@app.command(name="list")
def theme_list(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """List SDK-compatible themes below explicit roots."""

    try:
        roots = _roots(root)
    except ThemeError as exc:
        console.print(f"FAILED theme.list: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="validate")
def theme_validate(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Validate discovery, identity uniqueness, and SDK compatibility."""

    try:
        roots = _roots(root)
    except ThemeError as exc:
        console.print(f"FAILED theme.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


def _appearances(values: list[str] | None) -> tuple[ThemeAppearance, ...]:
    parsed: list[ThemeAppearance] = []
    for value in values or ():
        try:
            parsed.append(ThemeAppearance(value))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ThemeAppearance)
            raise ThemeError(f"Theme appearance must be one of: {allowed}.") from exc
    if len(set(parsed)) != len(parsed):
        raise ThemeError("Theme appearance filters must be unique.")
    return tuple(parsed)


@app.command(name="resolve")
def theme_resolve(
    theme_id: str,
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
    version: Annotated[str | None, typer.Option("--version")] = None,
    appearance: Annotated[list[str] | None, typer.Option("--appearance")] = None,
) -> None:
    """Resolve the highest compatible theme matching optional appearances."""

    try:
        roots = _roots(root)
        report = _validate(roots)
        if not report.passed:
            _print_report(report)
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
        record = ThemeCatalog(report.records).resolve(
            theme_id,
            version,
            appearances=_appearances(appearance),
        )
    except ThemeError as exc:
        console.print(f"FAILED theme.resolve: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(
        f"RESOLVED {record.theme_id} version={record.version} "
        f"root={record.root_id} path={record.relative_path}"
    )
    console.print(
        "Appearances: "
        + ", ".join(item.appearance.value for item in record.manifest.palettes)
    )
    console.print("Theme assets loaded: no")
    console.print("Styles applied: no")


__all__ = ["app"]
