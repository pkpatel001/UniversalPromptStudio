"""Closed E-017.1 inventory of safe self-generation artifact families."""

from __future__ import annotations

from .models import (
    SelfGenerationArtifactRule,
    SelfGenerationArtifactType,
    SelfGenerationTemplateKey,
)

SELF_GENERATION_ALLOWLIST: tuple[SelfGenerationArtifactRule, ...] = (
    SelfGenerationArtifactRule(
        SelfGenerationArtifactType.PACKAGE,
        SelfGenerationTemplateKey.PACKAGE_INIT,
        "Engineering/{package_name}/__init__.py",
    ),
    SelfGenerationArtifactRule(
        SelfGenerationArtifactType.MODULE,
        SelfGenerationTemplateKey.MODULE,
        "Engineering/{package_name}/{module_name}.py",
    ),
    SelfGenerationArtifactRule(
        SelfGenerationArtifactType.TEST,
        SelfGenerationTemplateKey.TEST,
        "Engineering/Tests/test_{module_name}.py",
    ),
    SelfGenerationArtifactRule(
        SelfGenerationArtifactType.DOCUMENTATION,
        SelfGenerationTemplateKey.DOCUMENTATION,
        "Engineering/{package_name}/README.md",
    ),
    SelfGenerationArtifactRule(
        SelfGenerationArtifactType.CLI_ADAPTER,
        SelfGenerationTemplateKey.CLI_ADAPTER,
        "Engineering/cli/commands/{module_name}.py",
        optional=True,
    ),
)


def self_generation_artifact_inventory() -> tuple[SelfGenerationArtifactRule, ...]:
    """Return the immutable allowlist in canonical plan order."""

    return SELF_GENERATION_ALLOWLIST
