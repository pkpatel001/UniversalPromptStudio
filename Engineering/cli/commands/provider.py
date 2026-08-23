"""Read-only CLI adapter for E-014 AI-provider metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import (
    ProviderCapability,
    ProviderCatalog,
    ProviderDiscoveryRoot,
    ProviderManifestReader,
    ProviderService,
    ProviderValidationReport,
)

app = typer.Typer(help="Inspect AI-provider SDK metadata without executing code")


@app.callback(invoke_without_command=True)
def provider_main(ctx: typer.Context) -> None:
    """Inspect AI-provider SDK metadata."""

    if ctx.invoked_subcommand is None:
        console.print(
            "Run 'python -m Engineering provider inspect MANIFEST' "
            "to validate provider metadata."
        )


@app.command(name="inspect")
def provider_inspect(manifest: Path) -> None:
    """Validate and display one exact AI-provider manifest."""

    try:
        parsed = ProviderManifestReader().read(manifest)
    except ProviderError as exc:
        console.print(f"FAILED provider.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    metadata = parsed.metadata
    console.print(f"Provider: {metadata.provider_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Entry point: {metadata.entry_point.value}")
    console.print(f"Transport: {metadata.transport.value}")
    console.print(f"Authentication: {metadata.authentication.value}")
    console.print(
        "Capabilities: " + ", ".join(capability.value for capability in parsed.capabilities)
    )
    console.print(f"Description: {metadata.description}")
    console.print("Provider code imported: no")
    console.print("Network requests: none")
    console.print("Credential access: none")


def _roots(values: list[Path] | None) -> tuple[ProviderDiscoveryRoot, ...]:
    if not values:
        raise ProviderError("Provider catalog commands require at least one explicit --root.")
    return tuple(
        ProviderDiscoveryRoot(f"explicit-{index:04d}", path)
        for index, path in enumerate(values, start=1)
    )


def _validate(roots: tuple[ProviderDiscoveryRoot, ...]) -> ProviderValidationReport:
    try:
        return ProviderService().validate_roots(roots)
    except ProviderError as exc:
        console.print(f"FAILED provider.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc


def _print_report(report: ProviderValidationReport) -> None:
    for record in report.records:
        metadata = record.manifest.metadata
        capabilities = ",".join(item.value for item in record.manifest.capabilities)
        console.print(
            f"VALID {record.provider_id} version={record.version} "
            f"sdk={metadata.sdk_version.api_level} "
            f"capabilities={capabilities} root={record.root_id} "
            f"path={record.relative_path}"
        )
    for issue in report.issues:
        console.print(
            f"FAILED {issue.code} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(report.summary)


@app.command(name="list")
def provider_list(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """List SDK-compatible providers below explicit roots."""

    try:
        roots = _roots(root)
    except ProviderError as exc:
        console.print(f"FAILED provider.list: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="validate")
def provider_validate(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Validate discovery, identity uniqueness, and SDK compatibility."""

    try:
        roots = _roots(root)
    except ProviderError as exc:
        console.print(f"FAILED provider.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


def _capabilities(values: list[str] | None) -> tuple[ProviderCapability, ...]:
    parsed: list[ProviderCapability] = []
    for value in values or ():
        try:
            parsed.append(ProviderCapability(value))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProviderCapability)
            raise ProviderError(f"Provider capability must be one of: {allowed}.") from exc
    if len(set(parsed)) != len(parsed):
        raise ProviderError("Provider capability filters must be unique.")
    return tuple(parsed)


@app.command(name="resolve")
def provider_resolve(
    provider_id: str,
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
    version: Annotated[str | None, typer.Option("--version")] = None,
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
) -> None:
    """Resolve the highest compatible provider matching optional capabilities."""

    try:
        roots = _roots(root)
        report = _validate(roots)
        if not report.passed:
            _print_report(report)
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
        record = ProviderCatalog(report.records).resolve(
            provider_id,
            version,
            capabilities=_capabilities(capability),
        )
    except ProviderError as exc:
        console.print(f"FAILED provider.resolve: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(
        f"RESOLVED {record.provider_id} version={record.version} "
        f"root={record.root_id} path={record.relative_path}"
    )
    console.print("Capabilities: " + ", ".join(item.value for item in record.manifest.capabilities))
    console.print("Provider code imported: no")
