"""Closed E-017.1 inventory of safe self-generation artifact families."""

from __future__ import annotations

from pathlib import PurePosixPath

from .models import (
    SelfGenerationArtifact,
    SelfGenerationArtifactRule,
    SelfGenerationArtifactType,
    SelfGenerationRequest,
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


def derive_self_generation_artifacts(
    request: SelfGenerationRequest,
) -> tuple[SelfGenerationArtifact, ...]:
    """Derive the canonical artifact set from the closed inventory."""

    return tuple(
        SelfGenerationArtifact(
            artifact_type=rule.artifact_type,
            template_key=rule.template_key,
            relative_path=PurePosixPath(
                rule.destination_pattern.format(
                    package_name=request.package_name,
                    module_name=request.module_name,
                )
            ),
        )
        for rule in SELF_GENERATION_ALLOWLIST
        if not rule.optional
        or (
            rule.artifact_type is SelfGenerationArtifactType.CLI_ADAPTER
            and request.include_cli_adapter
        )
    )
