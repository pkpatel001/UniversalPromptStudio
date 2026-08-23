"""E-015.2 theme discovery, compatibility, and catalog hardening tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ThemeError
from Engineering.ThemeSystem import (
    THEME_MANIFEST_NAME,
    ThemeAppearance,
    ThemeCatalog,
    ThemeDiscoveryRoot,
    ThemeDiscoveryService,
    ThemeSdkCompatibility,
    ThemeSdkContract,
    ThemeSdkVersion,
    ThemeService,
)


def _colors(primary: str = "#276A73") -> dict[str, str]:
    return {
        "canvas": "#F6F8F8",
        "surface": "#FFFFFF",
        "surface_muted": "#EDF3F2",
        "text": "#182026",
        "text_muted": "#627277",
        "border": "#DFE7E7",
        "primary": primary,
        "primary_text": "#FFFFFF",
        "sidebar": "#12181C",
        "sidebar_text": "#F7FBFB",
        "focus": "#2F7D89",
    }


def _data(
    theme_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    appearances: tuple[str, ...] = ("light",),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "theme": {
            "id": theme_id,
            "name": f"{theme_id} Theme",
            "version": version,
            "sdk_version": sdk_version,
            "description": f"Metadata for {theme_id}.",
            "default_appearance": appearances[0],
            "palettes": [
                {"appearance": appearance, "colors": _colors()}
                for appearance in appearances
            ],
        },
    }


def _write(
    root: Path,
    directory: str,
    theme_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    appearances: tuple[str, ...] = ("light",),
) -> Path:
    path = root / directory / THEME_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _data(
                theme_id,
                version,
                sdk_version=sdk_version,
                appearances=appearances,
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_sdk_contract_classifies_old_compatible_and_new_levels() -> None:
    contract = ThemeSdkContract(2, 3)

    assert contract.classify(ThemeSdkVersion(1)) == ThemeSdkCompatibility.TOO_OLD
    assert contract.classify(ThemeSdkVersion(2)) == ThemeSdkCompatibility.COMPATIBLE
    assert contract.classify(ThemeSdkVersion(4)) == ThemeSdkCompatibility.TOO_NEW


@pytest.mark.parametrize(("minimum", "maximum"), ((0, 1), (2, 1), (True, 1)))
def test_rejects_invalid_sdk_contracts(minimum: int, maximum: int) -> None:
    with pytest.raises(ThemeError, match="compatibility levels"):
        ThemeSdkContract(minimum, maximum)


def test_future_sdk_metadata_is_discovered_but_not_host_compatible(tmp_path: Path) -> None:
    _write(tmp_path, "future", "example.future-theme", sdk_version=2)

    inspection = ThemeDiscoveryService().inspect(tmp_path)
    validation = ThemeService().validate(tmp_path)

    assert inspection.passed
    assert inspection.records[0].manifest.metadata.sdk_version.api_level == 2
    assert not validation.passed
    assert validation.records == ()
    assert validation.issues[0].code == "theme.sdk.incompatible"
    assert "too-new" in validation.issues[0].message


def test_multi_root_discovery_is_stable_and_preserves_provenance(tmp_path: Path) -> None:
    project = tmp_path / "project"
    user = tmp_path / "user"
    _write(project, "zeta", "example.zeta-theme")
    _write(user, "alpha", "example.alpha-theme")

    report = ThemeService().validate_roots(
        (
            ThemeDiscoveryRoot("user", user),
            ThemeDiscoveryRoot("project", project),
        )
    )

    assert report.passed
    assert tuple((item.root_id, item.theme_id) for item in report.records) == (
        ("project", "example.zeta-theme"),
        ("user", "example.alpha-theme"),
    )


def test_duplicate_identity_across_roots_is_an_explicit_issue(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write(first, "one", "example.slate")
    _write(second, "two", "example.slate")

    report = ThemeDiscoveryService().inspect_roots(
        (
            ThemeDiscoveryRoot("first", first),
            ThemeDiscoveryRoot("second", second),
        )
    )

    assert not report.passed
    assert report.issues[0].code == "theme.identity.duplicate"
    assert "first:one/theme-manifest.yaml" in report.issues[0].message


def test_missing_root_and_duplicate_roots_are_explicit(tmp_path: Path) -> None:
    missing = ThemeDiscoveryService().inspect_roots(
        (ThemeDiscoveryRoot("missing", tmp_path / "missing"),)
    )
    first = tmp_path / "first"
    first.mkdir()

    assert missing.issues[0].code == "theme.root.missing"
    with pytest.raises(ThemeError, match="ids must be unique"):
        ThemeDiscoveryService().inspect_roots(
            (
                ThemeDiscoveryRoot("same", first),
                ThemeDiscoveryRoot("same", tmp_path),
            )
        )
    with pytest.raises(ThemeError, match="paths must be unique"):
        ThemeDiscoveryService().inspect_roots(
            (
                ThemeDiscoveryRoot("first", first),
                ThemeDiscoveryRoot("second", first),
            )
        )


def test_ignores_cache_directories_and_symlinked_directories(tmp_path: Path) -> None:
    _write(tmp_path / "node_modules", "ignored", "example.ignored-theme")
    _write(tmp_path, "valid", "example.valid-theme")
    original = Path.is_symlink

    def reported_as_symlink(path: Path) -> bool:
        return path.name == "linked" or original(path)

    linked = tmp_path / "linked"
    _write(linked, "nested", "example.linked-theme")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(Path, "is_symlink", reported_as_symlink)
        report = ThemeDiscoveryService().inspect(tmp_path)

    assert report.passed
    assert tuple(item.theme_id for item in report.records) == ("example.valid-theme",)


def test_catalog_resolves_highest_version_and_required_appearances(tmp_path: Path) -> None:
    _write(tmp_path, "v1", "example.slate", "1.0.0", appearances=("light",))
    _write(
        tmp_path,
        "v2",
        "example.slate",
        "2.0.0",
        appearances=("light", "dark"),
    )
    catalog = ThemeService().catalog(tmp_path)

    assert catalog.available_versions("example.slate") == ("1.0.0", "2.0.0")
    assert catalog.resolve("example.slate").version == "2.0.0"
    assert (
        catalog.resolve(
            "example.slate",
            appearances=(ThemeAppearance.DARK,),
        ).version
        == "2.0.0"
    )
    assert tuple(
        item.version for item in catalog.supporting((ThemeAppearance.LIGHT,))
    ) == ("1.0.0", "2.0.0")


def test_catalog_rejects_incompatible_and_unknown_appearance_match(tmp_path: Path) -> None:
    _write(tmp_path, "future", "example.future-theme", sdk_version=2)
    record = ThemeDiscoveryService().inspect(tmp_path).records[0]

    with pytest.raises(ThemeError, match="SDK API level 2"):
        ThemeCatalog((record,))
    with pytest.raises(ThemeError, match="Unknown compatible theme"):
        ThemeCatalog().resolve(
            "example.missing-theme",
            appearances=(ThemeAppearance.HIGH_CONTRAST,),
        )
    with pytest.raises(ThemeError, match="At least one"):
        ThemeCatalog().supporting(())


def test_cli_lists_validates_and_resolves_with_explicit_roots(tmp_path: Path) -> None:
    _write(tmp_path, "slate", "example.slate", appearances=("light", "dark"))
    runner = CliRunner()
    listed = runner.invoke(app, ["theme", "list", "--root", str(tmp_path)])
    validated = runner.invoke(app, ["theme", "validate", "--root", str(tmp_path)])
    resolved = runner.invoke(
        app,
        [
            "theme",
            "resolve",
            "example.slate",
            "--root",
            str(tmp_path),
            "--appearance",
            "dark",
        ],
    )

    assert listed.exit_code == 0
    assert "VALID example.slate version=1.0.0" in listed.output
    assert "Theme validation succeeded: 1 compatible, 0 issues" in listed.output
    assert validated.exit_code == 0
    assert resolved.exit_code == 0
    assert "RESOLVED example.slate version=1.0.0" in resolved.output
    assert "Styles applied: no" in resolved.output


def test_cli_requires_roots_and_rejects_unknown_appearance(tmp_path: Path) -> None:
    _write(tmp_path, "slate", "example.slate")
    runner = CliRunner()

    missing_root = runner.invoke(app, ["theme", "list"])
    unknown = runner.invoke(
        app,
        [
            "theme",
            "resolve",
            "example.slate",
            "--root",
            str(tmp_path),
            "--appearance",
            "sepia",
        ],
    )

    assert missing_root.exit_code == 1
    assert "explicit --root" in missing_root.output
    assert unknown.exit_code == 1
    assert "must be one of" in unknown.output


def test_theme_help_preserves_inspection_and_lists_catalog_commands() -> None:
    result = CliRunner().invoke(app, ["theme", "--help"])

    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "list" in result.output
    assert "resolve" in result.output
    assert "validate" in result.output
