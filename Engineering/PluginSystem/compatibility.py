"""SDK API-level compatibility policy for discovered plugin metadata."""

from __future__ import annotations

from dataclasses import dataclass

from Engineering.core.exceptions import PluginError

from .manifest import PLUGIN_SDK_API_LEVEL
from .models import (
    PluginIssue,
    PluginRecord,
    PluginSdkCompatibility,
    PluginSdkVersion,
)


@dataclass(frozen=True, slots=True)
class PluginSdkContract:
    """Inclusive SDK API-level range supported by one UPS host."""

    minimum_api_level: int = PLUGIN_SDK_API_LEVEL
    maximum_api_level: int = PLUGIN_SDK_API_LEVEL

    def __post_init__(self) -> None:
        if (
            type(self.minimum_api_level) is not int
            or type(self.maximum_api_level) is not int
            or self.minimum_api_level < 1
            or self.maximum_api_level < self.minimum_api_level
        ):
            raise PluginError(
                "Plugin SDK compatibility levels must be positive integers "
                "in ascending order."
            )

    def classify(self, version: PluginSdkVersion) -> PluginSdkCompatibility:
        """Classify a plugin API level without loading its entry point."""

        if version.api_level < self.minimum_api_level:
            return PluginSdkCompatibility.TOO_OLD
        if version.api_level > self.maximum_api_level:
            return PluginSdkCompatibility.TOO_NEW
        return PluginSdkCompatibility.COMPATIBLE

    def issue_for(self, record: PluginRecord) -> PluginIssue | None:
        """Return a deterministic issue for an incompatible plugin."""

        version = record.manifest.metadata.sdk_version
        compatibility = self.classify(version)
        if compatibility == PluginSdkCompatibility.COMPATIBLE:
            return None
        return PluginIssue(
            relative_path=record.relative_path,
            code="plugin.sdk.incompatible",
            message=(
                f"Plugin {record.plugin_id} version {record.version} declares "
                f"SDK API level {version.api_level} ({compatibility.value}); "
                f"supported levels are {self.minimum_api_level} through "
                f"{self.maximum_api_level}."
            ),
            root_id=record.root_id,
        )
