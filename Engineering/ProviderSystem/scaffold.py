"""Controlled E-014.3 provider scaffold generation through E-009 and E-008."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from Engineering.CodeGeneration import (
    ArtifactInfo,
    GenerationContext,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import ProviderError
from Engineering.Templates import TemplateExecutionResult, TemplateExecutor

from .manifest import (
    AI_PROVIDER_MANIFEST_NAME,
    AI_PROVIDER_SCHEMA_VERSION,
    ProviderManifestReader,
)
from .models import (
    ProviderAuthentication,
    ProviderCapability,
    ProviderEntryPoint,
    ProviderId,
    ProviderManifest,
    ProviderMetadata,
    ProviderSdkVersion,
    ProviderTransport,
    ProviderVersion,
)

PROVIDER_SCAFFOLD_TEMPLATE_ID = "provider.python-basic"
PROVIDER_SCAFFOLD_TEMPLATE_VERSION = "1.0.0"
_CLASS_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@dataclass(frozen=True, slots=True)
class ProviderScaffoldRequest:
    """Validated input for one project-local AI-provider scaffold."""

    provider_id: str
    name: str
    description: str
    version: str = "1.0.0"
    sdk_version: int = 1
    transport: str = ProviderTransport.LOCAL.value
    authentication: str = ProviderAuthentication.NONE.value
    capabilities: tuple[str, ...] = (ProviderCapability.TEXT_GENERATION.value,)
    class_name: str | None = None
    destination: str | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class ProviderScaffoldResult:
    """Expected provider metadata and delegated E-009 execution result."""

    destination: str
    provider_manifest: ProviderManifest
    execution: TemplateExecutionResult


class ProviderScaffoldService:
    """Compose provider metadata with E-009 templates and E-008 safe writes."""

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
    ) -> ProviderScaffoldService:
        return cls(TemplateExecutor.built_in(project_root), project, project_root)

    def generate(self, request: ProviderScaffoldRequest) -> ProviderScaffoldResult:
        """Generate a bounded passive scaffold without loading provider code."""

        class_name = request.class_name or self._default_class_name(request.provider_id)
        self._validate_class_name(class_name)
        destination = self._destination(request.provider_id, request.destination)
        manifest = self._manifest(request, class_name)
        values: dict[str, object] = {
            "provider_id": manifest.metadata.provider_id.value,
            "provider_name": manifest.metadata.name,
            "provider_version": manifest.metadata.version.value,
            "sdk_version": manifest.metadata.sdk_version.api_level,
            "description": manifest.metadata.description,
            "entry_point": manifest.metadata.entry_point.value,
            "class_name": class_name,
            "transport": manifest.metadata.transport.value,
            "authentication": manifest.metadata.authentication.value,
            "capabilities": [item.value for item in manifest.capabilities],
        }
        context = GenerationContext(
            project=self._project,
            generator=GeneratorInfo(
                generator_id=PROVIDER_SCAFFOLD_TEMPLATE_ID,
                name="Python AI-provider scaffold",
                version=PROVIDER_SCAFFOLD_TEMPLATE_VERSION,
            ),
            artifact=ArtifactInfo(
                name=manifest.metadata.name,
                description=manifest.metadata.description,
            ),
        )
        execution = self._executor.execute(
            PROVIDER_SCAFFOLD_TEMPLATE_ID,
            version=PROVIDER_SCAFFOLD_TEMPLATE_VERSION,
            destination=destination,
            context=context,
            values=values,
            overwrite=request.overwrite,
            dry_run=request.dry_run,
        )
        if execution.report.success and not request.dry_run:
            generated_path = self._project_root / destination / AI_PROVIDER_MANIFEST_NAME
            generated_manifest = ProviderManifestReader().read(generated_path)
            if generated_manifest != manifest:
                raise ProviderError(
                    "Generated provider manifest does not match the validated request."
                )
        return ProviderScaffoldResult(destination, manifest, execution)

    @staticmethod
    def _manifest(
        request: ProviderScaffoldRequest,
        class_name: str,
    ) -> ProviderManifest:
        capabilities: list[ProviderCapability] = []
        for value in request.capabilities:
            try:
                capabilities.append(ProviderCapability(value))
            except ValueError as exc:
                allowed = ", ".join(item.value for item in ProviderCapability)
                raise ProviderError(f"Provider capability must be one of: {allowed}.") from exc
        if len(set(capabilities)) != len(capabilities):
            raise ProviderError("Provider scaffold contains a duplicate capability.")
        try:
            transport = ProviderTransport(request.transport)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProviderTransport)
            raise ProviderError(f"Provider transport must be one of: {allowed}.") from exc
        try:
            authentication = ProviderAuthentication(request.authentication)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ProviderAuthentication)
            raise ProviderError(f"Provider authentication must be one of: {allowed}.") from exc
        return ProviderManifest(
            AI_PROVIDER_SCHEMA_VERSION,
            ProviderMetadata(
                ProviderId(request.provider_id),
                request.name,
                ProviderVersion(request.version),
                ProviderSdkVersion(request.sdk_version),
                request.description,
                ProviderEntryPoint(f"provider:{class_name}"),
                transport,
                authentication,
            ),
            tuple(sorted(capabilities, key=lambda item: item.value)),
        )

    @staticmethod
    def _default_class_name(provider_id: str) -> str:
        final_segment = provider_id.rsplit(".", 1)[-1]
        return "".join(part.capitalize() for part in final_segment.split("-")) + "Provider"

    @staticmethod
    def _validate_class_name(class_name: str) -> None:
        if not _CLASS_NAME.fullmatch(class_name):
            raise ProviderError("Provider class name must be a public Python class identifier.")

    @staticmethod
    def _destination(provider_id: str, supplied: str | None) -> str:
        value = supplied or f"Providers/{provider_id.replace('.', '-')}"
        value = value.replace("\\", "/")
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or len(path.parts) != 2
            or path.parts[0] != "Providers"
            or path.parts[1] in {"", ".", ".."}
            or ":" in value
        ):
            raise ProviderError(
                "Provider scaffold destination must be one direct child of Providers/."
            )
        return path.as_posix()


__all__ = [
    "PROVIDER_SCAFFOLD_TEMPLATE_ID",
    "PROVIDER_SCAFFOLD_TEMPLATE_VERSION",
    "ProviderScaffoldRequest",
    "ProviderScaffoldResult",
    "ProviderScaffoldService",
]
