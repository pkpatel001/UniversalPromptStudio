"""AI Provider SDK API-level compatibility policy."""

from __future__ import annotations

from dataclasses import dataclass

from Engineering.core.exceptions import ProviderError

from .manifest import AI_PROVIDER_SDK_API_LEVEL
from .models import (
    ProviderIssue,
    ProviderRecord,
    ProviderSdkCompatibility,
    ProviderSdkVersion,
)


@dataclass(frozen=True, slots=True)
class ProviderSdkContract:
    """Inclusive provider SDK API-level range supported by one host."""

    minimum_api_level: int = AI_PROVIDER_SDK_API_LEVEL
    maximum_api_level: int = AI_PROVIDER_SDK_API_LEVEL

    def __post_init__(self) -> None:
        if (
            type(self.minimum_api_level) is not int
            or type(self.maximum_api_level) is not int
            or self.minimum_api_level < 1
            or self.maximum_api_level < self.minimum_api_level
        ):
            raise ProviderError(
                "Provider SDK compatibility levels must be positive integers " "in ascending order."
            )

    def classify(self, version: ProviderSdkVersion) -> ProviderSdkCompatibility:
        if version.api_level < self.minimum_api_level:
            return ProviderSdkCompatibility.TOO_OLD
        if version.api_level > self.maximum_api_level:
            return ProviderSdkCompatibility.TOO_NEW
        return ProviderSdkCompatibility.COMPATIBLE

    def issue_for(self, record: ProviderRecord) -> ProviderIssue | None:
        version = record.manifest.metadata.sdk_version
        compatibility = self.classify(version)
        if compatibility == ProviderSdkCompatibility.COMPATIBLE:
            return None
        return ProviderIssue(
            record.relative_path,
            "provider.sdk.incompatible",
            (
                f"Provider {record.provider_id} version {record.version} declares "
                f"SDK API level {version.api_level} ({compatibility.value}); "
                f"supported levels are {self.minimum_api_level} through "
                f"{self.maximum_api_level}."
            ),
            record.root_id,
        )
