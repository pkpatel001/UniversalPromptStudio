"""Controlled E-015.3 theme scaffold generation through E-009 and E-008."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from Engineering.CodeGeneration import (
    ArtifactInfo,
    GenerationContext,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import ThemeError
from Engineering.Templates import TemplateExecutionResult, TemplateExecutor

from .manifest import THEME_MANIFEST_NAME, THEME_SCHEMA_VERSION, ThemeManifestReader
from .models import (
    ThemeAppearance,
    ThemeColor,
    ThemeId,
    ThemeManifest,
    ThemeMetadata,
    ThemePalette,
    ThemeSdkVersion,
    ThemeVersion,
)

THEME_SCAFFOLD_TEMPLATE_ID = "theme.declarative-basic"
THEME_SCAFFOLD_TEMPLATE_VERSION = "1.0.0"

_PALETTES: dict[ThemeAppearance, dict[str, str]] = {
    ThemeAppearance.LIGHT: {
        "canvas": "#F6F8F8",
        "surface": "#FFFFFF",
        "surface_muted": "#EDF3F2",
        "text": "#182026",
        "text_muted": "#627277",
        "border": "#DFE7E7",
        "primary": "#276A73",
        "primary_text": "#FFFFFF",
        "sidebar": "#12181C",
        "sidebar_text": "#F7FBFB",
        "focus": "#2F7D89",
    },
    ThemeAppearance.DARK: {
        "canvas": "#101417",
        "surface": "#182026",
        "surface_muted": "#243138",
        "text": "#F7FBFB",
        "text_muted": "#B8C7CA",
        "border": "#33434A",
        "primary": "#58A6B3",
        "primary_text": "#081012",
        "sidebar": "#0A0D0F",
        "sidebar_text": "#F7FBFB",
        "focus": "#72C7D2",
    },
    ThemeAppearance.HIGH_CONTRAST: {
        "canvas": "#000000",
        "surface": "#000000",
        "surface_muted": "#1A1A1A",
        "text": "#FFFFFF",
        "text_muted": "#FFFFFF",
        "border": "#FFFFFF",
        "primary": "#FFFF00",
        "primary_text": "#000000",
        "sidebar": "#000000",
        "sidebar_text": "#FFFFFF",
        "focus": "#00FFFF",
    },
}


@dataclass(frozen=True, slots=True)
class ThemeScaffoldRequest:
    """Validated input for one project-local declarative theme scaffold."""

    theme_id: str
    name: str
    description: str
    version: str = "1.0.0"
    sdk_version: int = 1
    default_appearance: str = ThemeAppearance.LIGHT.value
    appearances: tuple[str, ...] = (ThemeAppearance.LIGHT.value,)
    destination: str | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class ThemeScaffoldResult:
    """Expected theme metadata and delegated E-009 execution result."""

    destination: str
    theme_manifest: ThemeManifest
    execution: TemplateExecutionResult


class ThemeScaffoldService:
    """Compose theme metadata with E-009 templates and E-008 safe writes."""

    def __init__(
        self,
        executor: TemplateExecutor,
        project: ProjectGenerationInfo,
        project_root: Path,
    ) -> None:
        self._executor = executor
        self._project = project
        self._project_root = project_root.resolve()

    @classmethod
    def built_in(
        cls,
        project_root: Path,
        project: ProjectGenerationInfo,
    ) -> ThemeScaffoldService:
        return cls(TemplateExecutor.built_in(project_root), project, project_root)

    def generate(self, request: ThemeScaffoldRequest) -> ThemeScaffoldResult:
        """Generate a bounded declarative scaffold without applying a theme."""

        destination = self._destination(request.theme_id, request.destination)
        manifest = self._manifest(request)
        values: dict[str, object] = {
            "theme_id": manifest.metadata.theme_id.value,
            "theme_name": manifest.metadata.name,
            "theme_version": manifest.metadata.version.value,
            "sdk_version": manifest.metadata.sdk_version.api_level,
            "description": manifest.metadata.description,
            "default_appearance": manifest.default_appearance.value,
            "palettes": [self._palette_values(item) for item in manifest.palettes],
        }
        context = GenerationContext(
            project=self._project,
            generator=GeneratorInfo(
                generator_id=THEME_SCAFFOLD_TEMPLATE_ID,
                name="Declarative theme scaffold",
                version=THEME_SCAFFOLD_TEMPLATE_VERSION,
            ),
            artifact=ArtifactInfo(
                name=manifest.metadata.name,
                description=manifest.metadata.description,
            ),
        )
        execution = self._executor.execute(
            THEME_SCAFFOLD_TEMPLATE_ID,
            version=THEME_SCAFFOLD_TEMPLATE_VERSION,
            destination=destination,
            context=context,
            values=values,
            overwrite=request.overwrite,
            dry_run=request.dry_run,
        )
        if execution.report.success and not request.dry_run:
            generated_path = self._project_root / destination / THEME_MANIFEST_NAME
            generated_manifest = ThemeManifestReader().read(generated_path)
            if generated_manifest != manifest:
                raise ThemeError("Generated theme manifest does not match the validated request.")
        return ThemeScaffoldResult(destination, manifest, execution)

    @staticmethod
    def _manifest(request: ThemeScaffoldRequest) -> ThemeManifest:
        appearances: list[ThemeAppearance] = []
        for value in request.appearances:
            try:
                appearances.append(ThemeAppearance(value))
            except ValueError as exc:
                allowed = ", ".join(item.value for item in ThemeAppearance)
                raise ThemeError(f"Theme appearance must be one of: {allowed}.") from exc
        if len(set(appearances)) != len(appearances):
            raise ThemeError("Theme scaffold contains a duplicate appearance.")
        try:
            default = ThemeAppearance(request.default_appearance)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ThemeAppearance)
            raise ThemeError(f"Theme default appearance must be one of: {allowed}.") from exc
        palettes = tuple(
            sorted(
                (ThemeScaffoldService._palette(item) for item in appearances),
                key=lambda item: item.appearance.value,
            )
        )
        return ThemeManifest(
            THEME_SCHEMA_VERSION,
            ThemeMetadata(
                ThemeId(request.theme_id),
                request.name,
                ThemeVersion(request.version),
                ThemeSdkVersion(request.sdk_version),
                request.description,
            ),
            default,
            palettes,
        )

    @staticmethod
    def _palette(appearance: ThemeAppearance) -> ThemePalette:
        return ThemePalette(
            appearance=appearance,
            **{name: ThemeColor(value) for name, value in _PALETTES[appearance].items()},
        )

    @staticmethod
    def _palette_values(palette: ThemePalette) -> dict[str, object]:
        return {
            "appearance": palette.appearance.value,
            "colors": {
                name: getattr(palette, name).value
                for name in _PALETTES[palette.appearance]
            },
        }

    @staticmethod
    def _destination(theme_id: str, supplied: str | None) -> str:
        value = supplied or f"Themes/{theme_id.replace('.', '-')}"
        value = value.replace("\\", "/")
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or len(path.parts) != 2
            or path.parts[0] != "Themes"
            or path.parts[1] in {"", ".", ".."}
            or ":" in value
        ):
            raise ThemeError("Theme scaffold destination must be one direct child of Themes/.")
        return path.as_posix()


__all__ = [
    "THEME_SCAFFOLD_TEMPLATE_ID",
    "THEME_SCAFFOLD_TEMPLATE_VERSION",
    "ThemeScaffoldRequest",
    "ThemeScaffoldResult",
    "ThemeScaffoldService",
]
