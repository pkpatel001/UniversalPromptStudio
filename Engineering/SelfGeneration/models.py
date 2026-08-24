"""Immutable E-017.1 self-generation planning contracts."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from Engineering.core.exceptions import SelfGenerationError

_PACKAGE_NAME = re.compile(r"^[A-Z][A-Za-z0-9]{2,48}$")
_MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]{2,48}$")
_DISPLAY_NAME_MAX = 100
_DESCRIPTION_MAX = 500
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)


class SelfGenerationTarget(StrEnum):
    """Closed set of structures E-017 may plan."""

    ENGINEERING_SUBSYSTEM = "engineering-subsystem"


class SelfGenerationArtifactType(StrEnum):
    """Allowlisted output roles for the initial subsystem scaffold."""

    PACKAGE = "package"
    MODULE = "module"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CLI_ADAPTER = "cli-adapter"


class SelfGenerationTemplateKey(StrEnum):
    """Host-owned renderer keys; callers cannot provide template identifiers."""

    PACKAGE_INIT = "self-generation.package-init"
    MODULE = "self-generation.module"
    TEST = "self-generation.test"
    DOCUMENTATION = "self-generation.documentation"
    CLI_ADAPTER = "self-generation.cli-adapter"


class ToolkitMilestone(StrEnum):
    """Engineering capabilities required before self-generation is ready."""

    E_007 = "E-007"
    E_008 = "E-008"
    E_009 = "E-009"
    E_010 = "E-010"
    E_011 = "E-011"
    E_012 = "E-012"
    E_013 = "E-013"
    E_014 = "E-014"
    E_015 = "E-015"
    E_016 = "E-016"


@dataclass(frozen=True, slots=True)
class SelfGenerationRequest:
    """Validated request for one allowlisted Engineering subsystem plan."""

    package_name: str
    module_name: str
    display_name: str
    description: str
    include_cli_adapter: bool = False
    target: SelfGenerationTarget = SelfGenerationTarget.ENGINEERING_SUBSYSTEM

    def __post_init__(self) -> None:
        if self.target is not SelfGenerationTarget.ENGINEERING_SUBSYSTEM:
            raise SelfGenerationError("Unsupported self-generation target.")
        if (
            _PACKAGE_NAME.fullmatch(self.package_name) is None
            or self.package_name.lower() in _WINDOWS_RESERVED_NAMES
        ):
            raise SelfGenerationError(
                "Self-generation package_name must be a non-reserved 3-49 character "
                "PascalCase Python package name."
            )
        if (
            _MODULE_NAME.fullmatch(self.module_name) is None
            or "__" in self.module_name
            or keyword.iskeyword(self.module_name)
            or self.module_name in _WINDOWS_RESERVED_NAMES
        ):
            raise SelfGenerationError(
                "Self-generation module_name must be a non-reserved 3-49 character "
                "lowercase snake_case Python module name."
            )
        self._validate_text("display_name", self.display_name, _DISPLAY_NAME_MAX)
        self._validate_text("description", self.description, _DESCRIPTION_MAX)

    @staticmethod
    def _validate_text(field: str, value: str, maximum: int) -> None:
        if not value or value != value.strip():
            raise SelfGenerationError(f"Self-generation {field} must be non-empty trimmed text.")
        if len(value) > maximum or not value.isprintable():
            raise SelfGenerationError(
                f"Self-generation {field} must contain at most {maximum} printable characters."
            )


@dataclass(frozen=True, slots=True)
class SelfGenerationArtifactRule:
    """One host-owned artifact and destination pattern in the allowlist."""

    artifact_type: SelfGenerationArtifactType
    template_key: SelfGenerationTemplateKey
    destination_pattern: str
    optional: bool = False


@dataclass(frozen=True, slots=True)
class SelfGenerationArtifact:
    """One derived artifact in a read-only self-generation plan."""

    artifact_type: SelfGenerationArtifactType
    template_key: SelfGenerationTemplateKey
    relative_path: PurePosixPath


@dataclass(frozen=True, slots=True)
class SelfGenerationPrecondition:
    """One Engineering milestone capability and its repository evidence."""

    milestone: ToolkitMilestone
    capability: str
    evidence_paths: tuple[PurePosixPath, ...]


@dataclass(frozen=True, slots=True)
class SelfGenerationPreconditionResult:
    """Read-only result for one milestone precondition."""

    precondition: SelfGenerationPrecondition
    missing_paths: tuple[PurePosixPath, ...] = ()

    @property
    def satisfied(self) -> bool:
        return not self.missing_paths


@dataclass(frozen=True, slots=True)
class SelfGenerationPreconditionReport:
    """Stable readiness report covering E-007 through E-016."""

    results: tuple[SelfGenerationPreconditionResult, ...]

    @property
    def ready(self) -> bool:
        return all(result.satisfied for result in self.results)

    @property
    def satisfied_count(self) -> int:
        return sum(result.satisfied for result in self.results)


@dataclass(frozen=True, slots=True)
class SelfGenerationIssue:
    """One stable blocking issue discovered during planning."""

    code: str
    message: str
    location: str = ""


@dataclass(frozen=True, slots=True)
class SelfGenerationPlan:
    """Deterministic, non-executable description of approved future writes."""

    request: SelfGenerationRequest
    artifacts: tuple[SelfGenerationArtifact, ...]
    preconditions: SelfGenerationPreconditionReport
    issues: tuple[SelfGenerationIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return self.preconditions.ready and not self.issues


@dataclass(frozen=True, slots=True)
class SelfGenerationDryRunReport:
    """Stable human-readable projection of a self-generation plan."""

    plan: SelfGenerationPlan
    lines: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.plan.ready

    @property
    def summary(self) -> str:
        state = "ready" if self.ready else "blocked"
        return (
            f"Self-generation dry run {state}: {len(self.plan.artifacts)} artifact(s), "
            f"{len(self.plan.issues)} issue(s); no files written."
        )
