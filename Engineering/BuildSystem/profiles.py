"""Built-in build profiles for E-010."""

from __future__ import annotations

from .engine import BuildEngine
from .models import BuildProfile
from .steps import (
    BackendInventoryStep,
    FrontendReadinessStep,
    ProjectValidationStep,
    PythonSyntaxStep,
)

_PROFILE_TARGETS: dict[BuildProfile, tuple[str, ...]] = {
    BuildProfile.BACKEND: ("build.backend-inventory",),
    BuildProfile.FRONTEND: ("build.frontend-readiness",),
    BuildProfile.FULL: (
        "build.backend-inventory",
        "build.frontend-readiness",
    ),
}


def default_build_engine() -> BuildEngine:
    """Return the standard UPS build engine."""

    return BuildEngine(
        [
            ProjectValidationStep(),
            PythonSyntaxStep(),
            BackendInventoryStep(),
            FrontendReadinessStep(),
        ]
    )


def profile_targets(profile: BuildProfile) -> tuple[str, ...]:
    """Return terminal targets for a built-in profile."""

    return _PROFILE_TARGETS[profile]
