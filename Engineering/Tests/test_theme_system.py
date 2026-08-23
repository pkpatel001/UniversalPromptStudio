"""E-015.1 declarative theme SDK and manifest integration tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ThemeError
from Engineering.ManifestSystem import (
    ManifestKind,
    ManifestValidationService,
    default_manifest_adapters,
)
from Engineering.ThemeSystem import (
    THEME_MANIFEST_NAME,
    ThemeAppearance,
    ThemeManifestReader,
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


def _data(**theme_changes: object) -> dict[str, object]:
    theme: dict[str, object] = {
        "id": "example.slate",
        "name": "Slate",
        "version": "1.0.0",
        "sdk_version": 1,
        "description": "Declarative theme fixture.",
        "default_appearance": "light",
        "palettes": [
            {"appearance": "light", "colors": _colors()},
            {"appearance": "dark", "colors": _colors("#58A6B3")},
        ],
    }
    theme.update(theme_changes)
    return {"schema_version": 1, "theme": theme}


def _write(path: Path, data: dict[str, object] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data or _data(), sort_keys=False), encoding="utf-8")
    return path


def test_reads_typed_immutable_theme_and_sorts_appearances() -> None:
    manifest = ThemeManifestReader().read_text(yaml.safe_dump(_data(), sort_keys=False))

    assert manifest.metadata.theme_id.value == "example.slate"
    assert manifest.default_appearance == ThemeAppearance.LIGHT
    assert tuple(item.appearance for item in manifest.palettes) == (
        ThemeAppearance.DARK,
        ThemeAppearance.LIGHT,
    )
    assert manifest.palettes[0].primary.value == "#58A6B3"
    with pytest.raises(FrozenInstanceError):
        manifest.default_appearance = ThemeAppearance.DARK  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"id": "Slate"}, "Theme id"),
        ({"version": "1.0"}, "exactly major.minor.patch"),
        ({"sdk_version": True}, "must be an integer"),
        ({"default_appearance": "sepia"}, "must be one of"),
        ({"palettes": []}, "at least one palette"),
        (
            {
                "default_appearance": "high-contrast",
                "palettes": [{"appearance": "light", "colors": _colors()}],
            },
            "must have a matching palette",
        ),
        (
            {
                "palettes": [
                    {"appearance": "light", "colors": _colors()},
                    {"appearance": "light", "colors": _colors()},
                ]
            },
            "appearances must be unique",
        ),
    ),
)
def test_rejects_invalid_theme_contracts(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ThemeError, match=message):
        ThemeManifestReader().read_text(yaml.safe_dump(_data(**changes), sort_keys=False))


def test_rejects_invalid_color_missing_unknown_and_secret_like_fields() -> None:
    invalid_color = _data(
        palettes=[{"appearance": "light", "colors": _colors("rgb(0, 0, 0)")}]
    )
    missing = _data()
    assert isinstance(missing["theme"], dict)
    del missing["theme"]["description"]
    unknown = _data(author="Example")
    secret = _data(api_key="never-store")
    reader = ThemeManifestReader()

    with pytest.raises(ThemeError, match="#RRGGBB"):
        reader.read_text(yaml.safe_dump(invalid_color))
    with pytest.raises(ThemeError, match="missing keys: description"):
        reader.read_text(yaml.safe_dump(missing))
    with pytest.raises(ThemeError, match="unknown keys: author"):
        reader.read_text(yaml.safe_dump(unknown))
    with pytest.raises(ThemeError, match="Secret-like"):
        reader.read_text(yaml.safe_dump(secret))


@pytest.mark.parametrize(
    ("content", "message"),
    (
        ("- not-a-mapping\n", "root must be a mapping"),
        ("schema_version: [\n", "YAML is malformed"),
        ("schema_version: true\ntheme: {}\n", "must be an integer"),
    ),
)
def test_rejects_invalid_yaml_envelopes(content: str, message: str) -> None:
    with pytest.raises(ThemeError, match=message):
        ThemeManifestReader().read_text(content)


def test_shared_manifest_catalog_registers_plural_theme_family(tmp_path: Path) -> None:
    adapters = default_manifest_adapters()
    adapter = next(item for item in adapters if item.spec.manifest_id == "ups.theme")
    assert adapter.spec.kind == ManifestKind.THEME
    assert adapter.spec.allow_multiple
    _write(tmp_path / "one" / THEME_MANIFEST_NAME)
    _write(tmp_path / "two" / THEME_MANIFEST_NAME, _data(id="example.second-theme"))

    report = ManifestValidationService().validate(tmp_path)

    assert report.passed
    assert tuple(item.manifest_id for item in report.records) == (
        "ups.theme",
        "ups.theme",
    )


def test_theme_cli_inspects_without_loading_or_applying(tmp_path: Path) -> None:
    path = _write(tmp_path / THEME_MANIFEST_NAME)

    result = CliRunner().invoke(app, ["theme", "inspect", str(path)])

    assert result.exit_code == 0
    assert "Theme: example.slate" in result.output
    assert "Appearances: dark, light" in result.output
    assert "Theme assets loaded: no" in result.output
    assert "Styles applied: no" in result.output
    assert "Code executed: no" in result.output


def test_theme_cli_and_manifest_types_report_invalid_and_registered(tmp_path: Path) -> None:
    path = _write(tmp_path / THEME_MANIFEST_NAME, _data(palettes=[]))

    invalid = CliRunner().invoke(app, ["theme", "inspect", str(path)])
    types = CliRunner().invoke(app, ["manifest", "types"])
    help_result = CliRunner().invoke(app, ["theme", "--help"])

    assert invalid.exit_code == 1
    assert "at least one palette" in invalid.output
    assert types.exit_code == 0
    assert "ups.theme: theme-manifest.yaml" in types.output
    assert "cardinality: many" in types.output
    assert help_result.exit_code == 0
    assert "inspect" in help_result.output
