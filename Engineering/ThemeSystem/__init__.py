"""E-015 declarative theme SDK and manifest foundation."""

from .catalog import ThemeCatalog
from .compatibility import ThemeSdkContract
from .discovery import DEFAULT_IGNORED_THEME_DIRECTORIES, ThemeDiscoveryService
from .manifest import (
    THEME_MANIFEST_NAME,
    THEME_SCHEMA_VERSION,
    THEME_SDK_API_LEVEL,
    ThemeManifestReader,
)
from .models import (
    ThemeAppearance,
    ThemeColor,
    ThemeDiscoveryRoot,
    ThemeId,
    ThemeInspectionReport,
    ThemeIssue,
    ThemeManifest,
    ThemeMetadata,
    ThemePalette,
    ThemeRecord,
    ThemeSdkCompatibility,
    ThemeSdkVersion,
    ThemeValidationReport,
    ThemeVersion,
)
from .service import ThemeService

__all__ = [
    "THEME_MANIFEST_NAME",
    "THEME_SCHEMA_VERSION",
    "THEME_SDK_API_LEVEL",
    "DEFAULT_IGNORED_THEME_DIRECTORIES",
    "ThemeAppearance",
    "ThemeColor",
    "ThemeCatalog",
    "ThemeDiscoveryRoot",
    "ThemeDiscoveryService",
    "ThemeId",
    "ThemeInspectionReport",
    "ThemeIssue",
    "ThemeManifest",
    "ThemeManifestReader",
    "ThemeMetadata",
    "ThemePalette",
    "ThemeRecord",
    "ThemeSdkCompatibility",
    "ThemeSdkContract",
    "ThemeSdkVersion",
    "ThemeService",
    "ThemeValidationReport",
    "ThemeVersion",
]
