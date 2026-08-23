"""E-015.4 deterministic typed theme-token compilation tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ThemeError
from Engineering.ThemeSystem import (
    ThemeAppearance,
    ThemeColor,
    ThemeCssVariableSerializer,
    ThemeId,
    ThemeManifestReader,
    ThemeToken,
    ThemeTokenCompiler,
    ThemeTokenName,
    ThemeTokenSet,
    ThemeVersion,
)


def _colors(primary: str) -> dict[str, str]:
    return {
        "canvas": "#101417",
        "surface": "#182026",
        "surface_muted": "#243138",
        "text": "#F7FBFB",
        "text_muted": "#B8C7CA",
        "border": "#33434A",
        "primary": primary,
        "primary_text": "#081012",
        "sidebar": "#0A0D0F",
        "sidebar_text": "#F7FBFB",
        "focus": "#72C7D2",
    }


def _manifest_text() -> str:
    return yaml.safe_dump(
        {
            "schema_version": 1,
            "theme": {
                "id": "example.slate",
                "name": "Slate",
                "version": "1.2.3",
                "sdk_version": 1,
                "description": "Typed token fixture.",
                "default_appearance": "dark",
                "palettes": [
                    {"appearance": "light", "colors": _colors("#276A73")},
                    {"appearance": "dark", "colors": _colors("#58A6B3")},
                ],
            },
        },
        sort_keys=False,
    )


def _manifest_path(tmp_path: Path) -> Path:
    path = tmp_path / "theme-manifest.yaml"
    path.write_text(_manifest_text(), encoding="utf-8")
    return path


def test_compiles_default_palette_into_complete_ordered_typed_tokens() -> None:
    manifest = ThemeManifestReader().read_text(_manifest_text())

    result = ThemeTokenCompiler().compile(manifest)

    assert result.theme_id == ThemeId("example.slate")
    assert result.version == ThemeVersion("1.2.3")
    assert result.appearance == ThemeAppearance.DARK
    assert tuple(item.name for item in result.tokens) == tuple(ThemeTokenName)
    assert result.value_for(ThemeTokenName.PRIMARY) == ThemeColor("#58A6B3")
    assert len(result.tokens) == 11


def test_compiles_an_explicit_non_default_palette() -> None:
    manifest = ThemeManifestReader().read_text(_manifest_text())

    result = ThemeTokenCompiler().compile(manifest, ThemeAppearance.LIGHT)

    assert result.appearance == ThemeAppearance.LIGHT
    assert result.value_for(ThemeTokenName.PRIMARY).value == "#276A73"


def test_rejects_an_appearance_missing_from_the_manifest() -> None:
    manifest = ThemeManifestReader().read_text(_manifest_text())

    with pytest.raises(ThemeError, match="has no high-contrast palette"):
        ThemeTokenCompiler().compile(manifest, ThemeAppearance.HIGH_CONTRAST)


def test_serializes_selector_free_deterministic_css_variable_declarations() -> None:
    manifest = ThemeManifestReader().read_text(_manifest_text())
    token_set = ThemeTokenCompiler().compile(manifest)

    first = ThemeCssVariableSerializer().serialize(token_set)
    second = ThemeCssVariableSerializer().serialize(token_set)

    assert first == second
    assert first.splitlines()[0] == "--ups-color-canvas: #101417;"
    assert first.splitlines()[-1] == "--ups-color-focus: #72C7D2;"
    assert len(first.splitlines()) == 11
    assert "{" not in first
    assert "}" not in first
    assert "url(" not in first.lower()


def test_token_runtime_values_are_immutable_and_strictly_typed() -> None:
    token = ThemeToken(ThemeTokenName.CANVAS, ThemeColor("#101417"))

    assert token.css_variable == "--ups-color-canvas"
    with pytest.raises(FrozenInstanceError):
        token.value = ThemeColor("#FFFFFF")  # type: ignore[misc]
    with pytest.raises(ThemeError, match="name must be"):
        ThemeToken("canvas", ThemeColor("#101417"))  # type: ignore[arg-type]
    with pytest.raises(ThemeError, match="value must be"):
        ThemeToken(ThemeTokenName.CANVAS, "#101417")  # type: ignore[arg-type]


def test_token_set_rejects_partial_or_misordered_tokens() -> None:
    token = ThemeToken(ThemeTokenName.CANVAS, ThemeColor("#101417"))

    with pytest.raises(ThemeError, match="every semantic token"):
        ThemeTokenSet(
            ThemeId("example.slate"),
            ThemeVersion("1.2.3"),
            ThemeAppearance.DARK,
            (token,),
        )


def test_token_compiler_rejects_untyped_inputs() -> None:
    manifest = ThemeManifestReader().read_text(_manifest_text())
    compiler = ThemeTokenCompiler()

    with pytest.raises(ThemeError, match="requires ThemeManifest"):
        compiler.compile("manifest")  # type: ignore[arg-type]
    with pytest.raises(ThemeError, match="must be ThemeAppearance"):
        compiler.compile(manifest, "dark")  # type: ignore[arg-type]
    with pytest.raises(ThemeError, match="lookup name"):
        compiler.compile(manifest).value_for("primary")  # type: ignore[arg-type]


def test_cli_emits_default_and_explicit_palette_tokens_without_applying(
    tmp_path: Path,
) -> None:
    path = _manifest_path(tmp_path)
    runner = CliRunner()

    default = runner.invoke(app, ["theme", "tokens", str(path)])
    light = runner.invoke(
        app,
        ["theme", "tokens", str(path), "--appearance", "light"],
    )

    assert default.exit_code == 0
    assert "TOKENS example.slate version=1.2.3 appearance=dark count=11" in default.output
    assert "--ups-color-primary: #58A6B3;" in default.output
    assert "Selector emitted: no" in default.output
    assert "Styles applied: no" in default.output
    assert light.exit_code == 0
    assert "appearance=light count=11" in light.output
    assert "--ups-color-primary: #276A73;" in light.output


def test_cli_rejects_unknown_and_undeclared_appearances(tmp_path: Path) -> None:
    path = _manifest_path(tmp_path)
    runner = CliRunner()

    unknown = runner.invoke(
        app,
        ["theme", "tokens", str(path), "--appearance", "sepia"],
    )
    missing = runner.invoke(
        app,
        ["theme", "tokens", str(path), "--appearance", "high-contrast"],
    )

    assert unknown.exit_code == 1
    assert "FAILED theme.tokens" in unknown.output
    assert missing.exit_code == 1
    assert "has no high-contrast palette" in missing.output


def test_theme_help_lists_token_compilation() -> None:
    result = CliRunner().invoke(app, ["theme", "--help"])

    assert result.exit_code == 0
    assert "tokens" in result.output
