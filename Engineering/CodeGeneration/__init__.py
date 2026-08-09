"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Code Generation Framework

This package provides the deterministic, template-driven, validation-aware
artifact generation engine. All future UPS generators will consume this
framework rather than implementing ad-hoc file-writing logic.

Public API
----------
from Engineering.CodeGeneration import (
    GenerationEngine,
    GenerationPlan,
    GenerationReport,
    GenerationRequest,
    GenerationContext,
    TemplateRenderer,
    TemplateRepository,
    DirectoryTemplateRepository,
    ArtifactSpec,
    ArtifactState,
    OverwritePolicy,
)

===============================================================================
"""

from __future__ import annotations

from .engine import GenerationEngine
from .generator import Generator, StaticGenerator
from .models import (
    ArtifactInfo,
    ArtifactResult,
    ArtifactSpec,
    ArtifactState,
    GeneratedArtifact,
    GenerationContext,
    GenerationPlan,
    GenerationReport,
    GenerationRequest,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
    project_context_from_config,
)
from .planner import GenerationPlanner
from .policies import validate_destination, validate_no_secrets
from .registry import GeneratorRegistry
from .renderer import TemplateRenderer
from .templates import (
    DirectoryTemplateRepository,
    Template,
    TemplateRepository,
    auto_generated_header,
)

__all__ = [
    "GenerationEngine",
    "GenerationPlan",
    "GenerationReport",
    "GenerationRequest",
    "GenerationContext",
    "ProjectGenerationInfo",
    "GeneratorInfo",
    "ArtifactInfo",
    "ArtifactSpec",
    "ArtifactResult",
    "ArtifactState",
    "GeneratedArtifact",
    "OverwritePolicy",
    "project_context_from_config",
    "GenerationPlanner",
    "Generator",
    "StaticGenerator",
    "GeneratorRegistry",
    "TemplateRenderer",
    "Template",
    "TemplateRepository",
    "DirectoryTemplateRepository",
    "auto_generated_header",
    "validate_destination",
    "validate_no_secrets",
]
