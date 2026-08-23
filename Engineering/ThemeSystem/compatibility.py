"""Theme SDK API-level compatibility policy."""

from __future__ import annotations

from dataclasses import dataclass

from Engineering.core.exceptions import ThemeError

from .manifest import THEME_SDK_API_LEVEL
from .models import ThemeIssue, ThemeRecord, ThemeSdkCompatibility, ThemeSdkVersion


@dataclass(frozen=True, slots=True)
class ThemeSdkContract:
    """Inclusive Theme SDK API-level range supported by one host."""

    minimum_api_level: int = THEME_SDK_API_LEVEL
    maximum_api_level: int = THEME_SDK_API_LEVEL

    def __post_init__(self) -> None:
        if (
            type(self.minimum_api_level) is not int
            or type(self.maximum_api_level) is not int
            or self.minimum_api_level < 1
            or self.maximum_api_level < self.minimum_api_level
        ):
            raise ThemeError(
                "Theme SDK compatibility levels must be positive integers in ascending order."
            )

    def classify(self, version: ThemeSdkVersion) -> ThemeSdkCompatibility:
        if version.api_level < self.minimum_api_level:
            return ThemeSdkCompatibility.TOO_OLD
        if version.api_level > self.maximum_api_level:
            return ThemeSdkCompatibility.TOO_NEW
        return ThemeSdkCompatibility.COMPATIBLE

    def issue_for(self, record: ThemeRecord) -> ThemeIssue | None:
        version = record.manifest.metadata.sdk_version
        compatibility = self.classify(version)
        if compatibility == ThemeSdkCompatibility.COMPATIBLE:
            return None
        return ThemeIssue(
            record.relative_path,
            "theme.sdk.incompatible",
            (
                f"Theme {record.theme_id} version {record.version} declares "
                f"SDK API level {version.api_level} ({compatibility.value}); "
                f"supported levels are {self.minimum_api_level} through "
                f"{self.maximum_api_level}."
            ),
            record.root_id,
        )


__all__ = ["ThemeSdkContract"]
