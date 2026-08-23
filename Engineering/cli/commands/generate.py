"""Generate command group."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from Engineering.cli.output.console import console
from Engineering.CodeGeneration import (
    ArtifactInfo,
    GenerationContext,
    GeneratorInfo,
    OverwritePolicy,
    project_context_from_config,
)
from Engineering.core.config import get_config
from Engineering.core.exceptions import EngineeringError, GenerationValidationError
from Engineering.core.paths import get_paths
from Engineering.PluginSystem import (
    PluginDependency,
    PluginId,
    PluginScaffoldRequest,
    PluginScaffoldService,
)
from Engineering.ProviderSystem import (
    ProviderCapability,
    ProviderScaffoldRequest,
    ProviderScaffoldService,
)
from Engineering.Templates import (
    TemplateDefinition,
    TemplateExecutor,
    built_in_definition_repository,
)

app = typer.Typer(help="Generate project assets")
templates_app = typer.Typer(help="Discover and validate template definitions")


@app.callback(invoke_without_command=True)
def generate_main(ctx: typer.Context) -> None:
    """Generate project assets."""
    if ctx.invoked_subcommand is None:
        console.print("[yellow]Generation subsystem is not yet implemented.[/yellow]")


@templates_app.callback(invoke_without_command=True)
def list_templates(ctx: typer.Context) -> None:
    """List built-in template definitions."""

    if ctx.invoked_subcommand is not None:
        return
    definitions = built_in_definition_repository().definitions()
    if not definitions:
        console.print("[yellow]No template definitions found.[/yellow]")
        return
    for definition in definitions:
        console.print(
            f"[cyan]{definition.template_id}[/cyan] "
            f"v{definition.version} "
            f"[{definition.metadata.category.value}] "
            f"{definition.metadata.name}"
        )


@templates_app.command(name="inspect")
def inspect_template(template_id: str, version: str | None = None) -> None:
    """Display one built-in template definition."""

    definition = built_in_definition_repository().resolve(template_id, version)
    console.print(f"[bold cyan]{definition.template_id}[/bold cyan]")
    console.print(f"Version: {definition.version}")
    console.print(f"Name: {definition.metadata.name}")
    console.print(f"Category: {definition.metadata.category.value}")
    if definition.metadata.description:
        console.print(f"Description: {definition.metadata.description}")
    console.print("Variables:")
    for variable in definition.variables:
        console.print(
            f"  {variable.name}: {variable.value_type} ({variable.kind.value})"
        )
    console.print("Artifacts:")
    for artifact in definition.artifacts:
        console.print(
            f"  {artifact.relative_path} <- {artifact.source_template_id}"
        )


@templates_app.command(name="validate")
def validate_templates() -> None:
    """Validate all built-in template definitions and source references."""

    definitions = built_in_definition_repository().definitions()
    console.print(
        f"[green]Validated {len(definitions)} template definition(s).[/green]"
    )


@templates_app.command(name="run")
def run_template(
    template_id: str,
    destination: Annotated[str, typer.Option("--destination", "-d")],
    version: Annotated[str | None, typer.Option("--version")] = None,
    values: Annotated[list[str] | None, typer.Option("--value", "-v")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Generate artifacts from a built-in template definition."""

    definition = built_in_definition_repository().resolve(template_id, version)
    parsed_values = _parse_values(values or [], definition)
    config = get_config()
    context = GenerationContext(
        project=project_context_from_config(config),
        generator=GeneratorInfo(
            generator_id=definition.template_id,
            name=definition.metadata.name,
            version=definition.version,
        ),
        artifact=ArtifactInfo(name=definition.metadata.name),
    )
    result = TemplateExecutor.built_in(get_paths().root).execute(
        template_id,
        version=version,
        destination=destination,
        context=context,
        values=parsed_values,
        overwrite=OverwritePolicy.ALLOWED if overwrite else OverwritePolicy.NEVER,
        dry_run=dry_run,
    )
    console.print(result.report.summary)
    if result.manifest_path is not None:
        console.print(f"Manifest: {result.manifest_path}")
    if not result.report.success:
        raise typer.Exit(code=1)


def _parse_values(
    values: list[str], definition: TemplateDefinition
) -> dict[str, object]:
    """Parse repeatable NAME=VALUE options using declared variable types."""

    declared = {variable.name: variable.value_type for variable in definition.variables}
    parsed: dict[str, object] = {}
    for item in values:
        name, separator, raw = item.partition("=")
        if not separator or not name:
            raise GenerationValidationError(
                f"Template values must use NAME=VALUE syntax: {item!r}"
            )
        value_type = declared.get(name)
        if value_type is None:
            raise GenerationValidationError(f"Unknown template variable: {name!r}")
        if value_type == "string":
            parsed[name] = raw
            continue
        try:
            parsed[name] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GenerationValidationError(
                f"Invalid {value_type} value for {name!r}: {raw!r}"
            ) from exc
    return parsed


@app.command(name="provider")
def generate_provider(
    provider_id: str,
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    version: Annotated[str, typer.Option("--version")] = "1.0.0",
    sdk_version: Annotated[int, typer.Option("--sdk-version")] = 1,
    transport: Annotated[str, typer.Option("--transport")] = "local",
    authentication: Annotated[str, typer.Option("--authentication")] = "none",
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
    class_name: Annotated[str | None, typer.Option("--class-name")] = None,
    destination: Annotated[str | None, typer.Option("--destination", "-d")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Generate a controlled project-local Python AI-provider scaffold."""

    try:
        short_name = provider_id.rsplit(".", 1)[-1].replace("-", " ").title()
        request = ProviderScaffoldRequest(
            provider_id=provider_id,
            name=name or f"{short_name} Provider",
            description=description or f"UPS AI provider {provider_id}.",
            version=version,
            sdk_version=sdk_version,
            transport=transport,
            authentication=authentication,
            capabilities=tuple(capability or (ProviderCapability.TEXT_GENERATION.value,)),
            class_name=class_name,
            destination=destination,
            overwrite=(
                OverwritePolicy.ALLOWED if overwrite else OverwritePolicy.NEVER
            ),
            dry_run=dry_run,
        )
        result = ProviderScaffoldService.built_in(
            get_paths().root,
            project_context_from_config(get_config()),
        ).generate(request)
    except EngineeringError as exc:
        console.print(f"FAILED provider.generate: {exc}", soft_wrap=True)
        raise typer.Exit(code=1) from exc

    console.print(result.execution.report.summary)
    console.print(f"Destination: {result.destination}")
    if result.execution.manifest_path is not None:
        console.print(f"Artifact manifest: {result.execution.manifest_path}")
    if not result.execution.report.success:
        raise typer.Exit(code=1)


@app.command(name="plugin")
def generate_plugin(
    plugin_id: str,
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    version: Annotated[str, typer.Option("--version")] = "1.0.0",
    sdk_version: Annotated[int, typer.Option("--sdk-version")] = 1,
    capability: Annotated[list[str] | None, typer.Option("--capability")] = None,
    permission: Annotated[list[str] | None, typer.Option("--permission")] = None,
    dependency: Annotated[list[str] | None, typer.Option("--dependency")] = None,
    class_name: Annotated[str | None, typer.Option("--class-name")] = None,
    destination: Annotated[str | None, typer.Option("--destination", "-d")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Generate a controlled project-local Python plugin scaffold."""

    try:
        short_name = plugin_id.rsplit(".", 1)[-1].replace("-", " ").title()
        request = PluginScaffoldRequest(
            plugin_id=plugin_id,
            name=name or f"{short_name} Plugin",
            description=description or f"UPS plugin {plugin_id}.",
            version=version,
            sdk_version=sdk_version,
            capabilities=tuple(capability or ()),
            permissions=tuple(permission or ()),
            dependencies=_parse_dependencies(dependency or ()),
            class_name=class_name,
            destination=destination,
            overwrite=(
                OverwritePolicy.ALLOWED if overwrite else OverwritePolicy.NEVER
            ),
            dry_run=dry_run,
        )
        result = PluginScaffoldService.built_in(
            get_paths().root,
            project_context_from_config(get_config()),
        ).generate(request)
    except EngineeringError as exc:
        console.print(f"FAILED plugin.generate: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(result.execution.report.summary)
    console.print(f"Destination: {result.destination}")
    if result.execution.manifest_path is not None:
        console.print(f"Artifact manifest: {result.execution.manifest_path}")
    if not result.execution.report.success:
        raise typer.Exit(code=1)


def _parse_dependencies(values: list[str] | tuple[str, ...]) -> tuple[PluginDependency, ...]:
    """Parse repeatable PLUGIN_ID=SPECIFIER dependency options."""

    parsed: list[PluginDependency] = []
    for value in values:
        plugin_id, separator, specifier = value.partition("=")
        if not separator or not plugin_id or not specifier:
            raise GenerationValidationError(
                "Plugin dependencies must use PLUGIN_ID=SPECIFIER syntax: "
                f"{value!r}"
            )
        parsed.append(PluginDependency(PluginId(plugin_id), specifier))
    return tuple(parsed)


app.add_typer(templates_app, name="templates")
