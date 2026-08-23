"""Controlled E-013.3 plugin scaffold generation through E-009 and E-008."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from Engineering.CodeGeneration import (
    ArtifactInfo,
    GenerationContext,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)
from Engineering.core.exceptions import PluginError
from Engineering.Templates import TemplateExecutionResult, TemplateExecutor

from .manifest import (
    PLUGIN_MANIFEST_NAME,
    PLUGIN_SCHEMA_VERSION,
    PluginManifestReader,
)
from .models import (
    PluginCapability,
    PluginDependency,
    PluginEntryPoint,
    PluginId,
    PluginManifest,
    PluginMetadata,
    PluginPermission,
    PluginSdkVersion,
    PluginVersion,
)

PLUGIN_SCAFFOLD_TEMPLATE_ID = "plugin.python-basic"
PLUGIN_SCAFFOLD_TEMPLATE_VERSION = "1.0.0"
_CLASS_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@dataclass(frozen=True, slots=True)
class PluginScaffoldRequest:
    """Validated input for one project-local plugin scaffold."""

    plugin_id: str
    name: str
    description: str
    version: str = "1.0.0"
    sdk_version: int = 1
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    dependencies: tuple[PluginDependency, ...] = ()
    class_name: str | None = None
    destination: str | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class PluginScaffoldResult:
    """Expected plugin metadata and the delegated E-009 execution result."""

    destination: str
    plugin_manifest: PluginManifest
    execution: TemplateExecutionResult


class PluginScaffoldService:
    """Compose plugin metadata with E-009 templates and E-008 safe writes."""

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
    ) -> PluginScaffoldService:
        """Build the service with the repository's built-in templates."""

        return cls(TemplateExecutor.built_in(project_root), project, project_root)

    def generate(self, request: PluginScaffoldRequest) -> PluginScaffoldResult:
        """Generate a bounded scaffold without installing or loading it."""

        class_name = request.class_name or self._default_class_name(request.plugin_id)
        self._validate_class_name(class_name)
        destination = self._destination(request.plugin_id, request.destination)
        manifest = self._manifest(request, class_name)
        values: dict[str, object] = {
            "plugin_id": manifest.metadata.plugin_id.value,
            "plugin_name": manifest.metadata.name,
            "plugin_version": manifest.metadata.version.value,
            "sdk_version": manifest.metadata.sdk_version.api_level,
            "description": manifest.metadata.description,
            "entry_point": manifest.metadata.entry_point.value,
            "class_name": class_name,
            "capabilities": [
                item.capability_id for item in manifest.capabilities
            ],
            "permissions": [item.permission_id for item in manifest.permissions],
            "dependencies": [
                {
                    "id": item.plugin_id.value,
                    "version": item.version_specifier,
                }
                for item in manifest.dependencies
            ],
        }
        context = GenerationContext(
            project=self._project,
            generator=GeneratorInfo(
                generator_id=PLUGIN_SCAFFOLD_TEMPLATE_ID,
                name="Python plugin scaffold",
                version=PLUGIN_SCAFFOLD_TEMPLATE_VERSION,
            ),
            artifact=ArtifactInfo(
                name=manifest.metadata.name,
                description=manifest.metadata.description,
            ),
        )
        execution = self._executor.execute(
            PLUGIN_SCAFFOLD_TEMPLATE_ID,
            version=PLUGIN_SCAFFOLD_TEMPLATE_VERSION,
            destination=destination,
            context=context,
            values=values,
            overwrite=request.overwrite,
            dry_run=request.dry_run,
        )
        if execution.report.success and not request.dry_run:
            generated_path = self._project_root / destination / PLUGIN_MANIFEST_NAME
            generated_manifest = PluginManifestReader().read(generated_path)
            if generated_manifest != manifest:
                raise PluginError(
                    "Generated plugin manifest does not match the validated request."
                )
        return PluginScaffoldResult(destination, manifest, execution)

    @staticmethod
    def _manifest(
        request: PluginScaffoldRequest,
        class_name: str,
    ) -> PluginManifest:
        plugin_id = PluginId(request.plugin_id)
        capabilities = tuple(
            sorted(
                (PluginCapability(value) for value in request.capabilities),
                key=lambda item: item.capability_id,
            )
        )
        permissions = tuple(
            sorted(
                (PluginPermission(value) for value in request.permissions),
                key=lambda item: item.permission_id,
            )
        )
        PluginScaffoldService._require_unique(
            (item.capability_id for item in capabilities), "capability"
        )
        PluginScaffoldService._require_unique(
            (item.permission_id for item in permissions), "permission"
        )
        dependencies = tuple(
            sorted(request.dependencies, key=lambda item: item.plugin_id.value)
        )
        PluginScaffoldService._require_unique(
            (item.plugin_id.value for item in dependencies), "dependency"
        )
        if any(item.plugin_id == plugin_id for item in dependencies):
            raise PluginError("A plugin cannot depend on itself.")
        return PluginManifest(
            schema_version=PLUGIN_SCHEMA_VERSION,
            metadata=PluginMetadata(
                plugin_id=plugin_id,
                name=request.name,
                version=PluginVersion(request.version),
                sdk_version=PluginSdkVersion(request.sdk_version),
                description=request.description,
                entry_point=PluginEntryPoint(f"plugin:{class_name}"),
            ),
            capabilities=capabilities,
            permissions=permissions,
            dependencies=dependencies,
        )

    @staticmethod
    def _require_unique(values: Iterable[str], label: str) -> None:
        items = tuple(values)
        if len(set(items)) != len(items):
            raise PluginError(f"Plugin scaffold contains a duplicate {label}.")

    @staticmethod
    def _default_class_name(plugin_id: str) -> str:
        final_segment = plugin_id.rsplit(".", 1)[-1]
        return "".join(part.capitalize() for part in final_segment.split("-")) + "Plugin"

    @staticmethod
    def _validate_class_name(class_name: str) -> None:
        if not _CLASS_NAME.fullmatch(class_name):
            raise PluginError(
                "Plugin class name must be a public Python class identifier."
            )

    @staticmethod
    def _destination(plugin_id: str, supplied: str | None) -> str:
        value = supplied or f"Plugins/{plugin_id.replace('.', '-')}"
        value = value.replace("\\", "/")
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or len(path.parts) != 2
            or path.parts[0] != "Plugins"
            or path.parts[1] in {"", ".", ".."}
            or ":" in value
        ):
            raise PluginError(
                "Plugin scaffold destination must be one direct child of Plugins/."
            )
        return path.as_posix()


__all__ = [
    "PLUGIN_SCAFFOLD_TEMPLATE_ID",
    "PLUGIN_SCAFFOLD_TEMPLATE_VERSION",
    "PluginScaffoldRequest",
    "PluginScaffoldResult",
    "PluginScaffoldService",
]
