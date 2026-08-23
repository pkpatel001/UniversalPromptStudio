"""Read-only CLI adapter for E-015 theme metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ThemeError
from Engineering.core.paths import get_paths
from Engineering.ThemeSystem import (
    ThemeAppearance,
    ThemeCatalog,
    ThemeCssVariableSerializer,
    ThemeDiscoveryRoot,
    ThemeFrontendCatalogSynchronizer,
    ThemeInstallationPlanner,
    ThemeInstaller,
    ThemeInstallPlan,
    ThemeLifecycleAction,
    ThemeLifecycleManager,
    ThemeLifecyclePlan,
    ThemeLifecyclePlanner,
    ThemeManagedThemeService,
    ThemeManifestReader,
    ThemePackageInspector,
    ThemeService,
    ThemeTokenCompiler,
    ThemeValidationReport,
)

app = typer.Typer(help="Inspect declarative theme metadata without applying styles")
package_app = typer.Typer(help="Inspect canonical data-only theme packages")
install_app = typer.Typer(help="Plan or apply controlled external-theme installation")


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


@package_app.command(name="inspect")
def theme_package_inspect(package: Path) -> None:
    """Inspect and hash one canonical theme ZIP without extraction."""

    try:
        inspected = ThemePackageInspector().inspect(package)
    except ThemeError as exc:
        console.print(f"FAILED theme.package.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(
        f"PACKAGE {inspected.theme_id} version={inspected.version} "
        f"sdk={inspected.manifest.metadata.sdk_version.api_level}"
    )
    console.print(f"Archive: {inspected.filename}")
    console.print(f"SHA-256: {inspected.sha256}")
    console.print(f"Manifest SHA-256: {inspected.entries[0].sha256}")
    console.print("Package contents: theme-manifest.yaml only")
    console.print("Publisher authentication: unavailable")
    console.print("Archive extracted: no")
    console.print("Styles applied: no")


def _theme_install_root(root: Path | None) -> ThemeDiscoveryRoot:
    return ThemeDiscoveryRoot("project", root or (get_paths().root / "Themes"))


def _print_install_plan(plan: ThemeInstallPlan) -> None:
    console.print(f"PACKAGE {plan.package.theme_id} version={plan.package.version}")
    console.print(f"SHA-256: {plan.package.sha256}")
    console.print(f"Trust: {plan.trust.status.value} (exact package bytes only)")
    console.print(f"Target: {plan.root_id}:{plan.target_relative_path}")
    for issue in plan.issues:
        console.print(
            f"BLOCKED {issue.code} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(plan.summary)


@install_app.command(name="plan")
def theme_install_plan(
    package: Path,
    root: Annotated[Path | None, typer.Option("--root")] = None,
    approved_sha256: Annotated[
        str | None, typer.Option("--approve-sha256")
    ] = None,
    acknowledge_external_theme: Annotated[
        bool, typer.Option("--acknowledge-external-theme")
    ] = False,
) -> None:
    """Plan installation without writing, extracting, syncing, or applying."""

    try:
        plan = ThemeInstallationPlanner().plan(
            package,
            _theme_install_root(root),
            approved_sha256=approved_sha256,
            acknowledge_external_theme=acknowledge_external_theme,
        )
        _print_install_plan(plan)
    except ThemeError as exc:
        console.print(f"FAILED theme.install.plan: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print("Filesystem changes: none")
    if not plan.ready:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@install_app.command(name="apply")
def theme_install_apply(
    package: Path,
    approved_sha256: Annotated[str, typer.Option("--approve-sha256")],
    source_label: Annotated[str, typer.Option("--source-label")],
    acknowledge_external_theme: Annotated[
        bool, typer.Option("--acknowledge-external-theme")
    ] = False,
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Install one exact approved external theme into the managed local root."""

    install_root = _theme_install_root(root)
    try:
        plan = ThemeInstallationPlanner().plan(
            package,
            install_root,
            approved_sha256=approved_sha256,
            acknowledge_external_theme=acknowledge_external_theme,
        )
        _print_install_plan(plan)
        if not plan.ready:
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
        result = ThemeInstaller().install(
            plan,
            install_root.path,
            source_label=source_label,
        )
    except ThemeError as exc:
        console.print(f"FAILED theme.install.apply: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(f"INSTALLED {result.theme_id} version={result.version}")
    console.print(f"Target: {result.target}")
    console.print(f"Provenance receipt: {result.receipt}")
    console.print("Frontend catalog synchronized: no")
    console.print("Theme activated: no")


@install_app.command(name="verify")
def theme_install_verify(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Verify active and disabled managed themes against provenance receipts."""

    try:
        report = ThemeManagedThemeService().verify(_theme_install_root(root))
    except ThemeError as exc:
        console.print(f"FAILED theme.install.verify: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    for record in report.records:
        console.print(
            f"VERIFIED {record.theme_id} version={record.version} "
            f"state={record.state.value} package-sha256={record.receipt.package_sha256}"
        )
    for issue in report.issues:
        console.print(
            f"FAILED {issue.code} state={issue.state.value} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(report.summary)
    console.print("Filesystem changes: none")
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


def _print_lifecycle_plan(plan: ThemeLifecyclePlan) -> None:
    console.print(
        f"THEME {plan.theme_id} version={plan.version} action={plan.action.value}"
    )
    if plan.record is not None:
        console.print(f"Package SHA-256: {plan.record.receipt.package_sha256}")
        console.print(f"Manifest SHA-256: {plan.record.receipt.manifest_sha256}")
    console.print(f"Source: {plan.root_id}:{plan.source_relative_path}")
    console.print(f"Target: {plan.root_id}:{plan.target_relative_path}")
    for issue in plan.issues:
        console.print(
            f"BLOCKED {issue.code} state={issue.state.value} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(plan.summary)


def _theme_lifecycle(
    action: ThemeLifecycleAction,
    theme_id: str,
    version: str,
    root: Path | None,
    approved_package_sha256: str | None,
    acknowledged: bool,
    apply: bool,
) -> None:
    lifecycle_root = _theme_install_root(root)
    try:
        plan = ThemeLifecyclePlanner().plan(
            lifecycle_root,
            theme_id,
            version,
            action,
            approved_package_sha256=approved_package_sha256,
            acknowledge_lifecycle_change=acknowledged,
        )
        _print_lifecycle_plan(plan)
        if not plan.ready:
            raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
        if not apply:
            console.print("Filesystem changes: none")
            return
        result = ThemeLifecycleManager().apply(plan, lifecycle_root.path)
    except ThemeError as exc:
        console.print(
            f"FAILED theme.install.{action.value}: {exc}",
            soft_wrap=True,
        )
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(
        f"{result.action.value.upper()}D {result.theme_id} version={result.version}"
    )
    console.print(f"Target: {result.target}")
    console.print("Frontend catalog synchronized: no")
    console.print("Theme activated: no")


@install_app.command(name="disable")
def theme_install_disable(
    theme_id: str,
    version: Annotated[str, typer.Option("--version")],
    approved_package_sha256: Annotated[
        str | None, typer.Option("--approve-package-sha256")
    ] = None,
    acknowledge_disable: Annotated[
        bool, typer.Option("--acknowledge-disable")
    ] = False,
    apply: Annotated[bool, typer.Option("--apply")] = False,
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Plan or explicitly apply a reversible managed-theme disable."""

    _theme_lifecycle(
        ThemeLifecycleAction.DISABLE,
        theme_id,
        version,
        root,
        approved_package_sha256,
        acknowledge_disable,
        apply,
    )


@install_app.command(name="restore")
def theme_install_restore(
    theme_id: str,
    version: Annotated[str, typer.Option("--version")],
    approved_package_sha256: Annotated[
        str | None, typer.Option("--approve-package-sha256")
    ] = None,
    acknowledge_restore: Annotated[
        bool, typer.Option("--acknowledge-restore")
    ] = False,
    apply: Annotated[bool, typer.Option("--apply")] = False,
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Plan or explicitly apply restoration of one disabled managed theme."""

    _theme_lifecycle(
        ThemeLifecycleAction.RESTORE,
        theme_id,
        version,
        root,
        approved_package_sha256,
        acknowledge_restore,
        apply,
    )


@app.command(name="tokens")
def theme_tokens(
    manifest: Path,
    appearance: Annotated[str | None, typer.Option("--appearance")] = None,
) -> None:
    """Compile one manifest palette into selector-free CSS variables."""

    try:
        parsed = ThemeManifestReader().read(manifest)
        selected = ThemeAppearance(appearance) if appearance is not None else None
        token_set = ThemeTokenCompiler().compile(parsed, selected)
        declarations = ThemeCssVariableSerializer().serialize(token_set)
    except (ThemeError, ValueError) as exc:
        console.print(f"FAILED theme.tokens: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(
        f"TOKENS {token_set.theme_id.value} version={token_set.version.value} "
        f"appearance={token_set.appearance.value} count={len(token_set.tokens)}"
    )
    console.print(declarations)
    console.print("Selector emitted: no")
    console.print("Styles applied: no")


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


@app.command(name="sync-frontend")
def theme_sync_frontend(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
    check: Annotated[bool, typer.Option("--check")] = False,
) -> None:
    """Check or update the exact generated frontend theme catalog."""

    try:
        roots = _roots(root)
        catalog = ThemeService().catalog_roots(roots)
        result = ThemeFrontendCatalogSynchronizer().synchronize(
            get_paths().root,
            catalog,
            check=check,
        )
    except ThemeError as exc:
        console.print(f"FAILED theme.sync-frontend: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    if check and not result.current:
        console.print(f"FAILED frontend theme catalog is stale: {result.path}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
    action = "updated" if result.changed else "current"
    console.print(f"Frontend theme catalog {action}: {result.path}")
    console.print(f"Selections transported: {result.selection_count}")


app.add_typer(package_app, name="package")
app.add_typer(install_app, name="install")


__all__ = ["app"]
