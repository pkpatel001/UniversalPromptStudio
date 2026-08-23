"""Controlled E-015.6 theme catalog transport to one frontend module."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .catalog import ThemeCatalog
from .models import ThemeAppearance, ThemeId, ThemeVersion
from .tokens import ThemeToken, ThemeTokenCompiler, ThemeTokenName

FRONTEND_THEME_CATALOG_SCHEMA_VERSION = 1
FRONTEND_THEME_CATALOG_PATH = Path(
    "Frontend/src/generated/theme-catalog.generated.js"
)
_MAXIMUM_CATALOG_BYTES = 1_000_000
_FRONTEND_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True, slots=True)
class ThemeFrontendSelection:
    """One identity-bound appearance transported to the frontend."""

    theme_id: ThemeId
    theme_name: str
    version: ThemeVersion
    appearance: ThemeAppearance
    tokens: tuple[ThemeToken, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.theme_id, ThemeId):
            raise ThemeError("Frontend theme selection theme_id must be ThemeId.")
        if not self.theme_name or len(self.theme_name) > 120:
            raise ThemeError("Frontend theme selection requires a bounded theme name.")
        if not isinstance(self.version, ThemeVersion):
            raise ThemeError("Frontend theme selection version must be ThemeVersion.")
        if _FRONTEND_VERSION.fullmatch(self.version.value) is None:
            raise ThemeError(
                "Frontend theme selection version must use major.minor.patch."
            )
        if not isinstance(self.appearance, ThemeAppearance):
            raise ThemeError(
                "Frontend theme selection appearance must be ThemeAppearance."
            )
        if tuple(item.name for item in self.tokens) != tuple(ThemeTokenName):
            raise ThemeError(
                "Frontend theme selection must contain every semantic token in host order."
            )


@dataclass(frozen=True, slots=True)
class ThemeFrontendCatalog:
    """Versioned deterministic frontend transport document."""

    schema_version: int
    selections: tuple[ThemeFrontendSelection, ...]

    def __post_init__(self) -> None:
        if self.schema_version != FRONTEND_THEME_CATALOG_SCHEMA_VERSION:
            raise ThemeError("Frontend theme catalog schema_version must be integer 1.")
        if not self.selections:
            raise ThemeError("Frontend theme catalog requires at least one selection.")
        keys = tuple(self._identity_key(item) for item in self.selections)
        if len(set(keys)) != len(keys):
            raise ThemeError("Frontend theme catalog selections must be unique.")
        ordered = tuple(sorted(self.selections, key=self._order_key))
        if self.selections != ordered:
            raise ThemeError("Frontend theme catalog selections must use stable host order.")

    @staticmethod
    def _identity_key(item: ThemeFrontendSelection) -> tuple[str, str, str]:
        return (
            item.theme_id.value,
            item.version.value,
            item.appearance.value,
        )

    @staticmethod
    def _order_key(
        item: ThemeFrontendSelection,
    ) -> tuple[str, tuple[int, ...], str]:
        return (
            item.theme_id.value,
            item.version.parsed.release,
            item.appearance.value,
        )


class ThemeFrontendCatalogCompiler:
    """Compile every compatible catalog palette into transport selections."""

    def __init__(self, token_compiler: ThemeTokenCompiler | None = None) -> None:
        self._token_compiler = token_compiler or ThemeTokenCompiler()

    def compile(self, catalog: ThemeCatalog) -> ThemeFrontendCatalog:
        if not isinstance(catalog, ThemeCatalog):
            raise ThemeError("Frontend theme transport requires ThemeCatalog.")
        selections = []
        for record in catalog.records:
            metadata = record.manifest.metadata
            for palette in record.manifest.palettes:
                token_set = self._token_compiler.compile(
                    record.manifest,
                    palette.appearance,
                )
                selections.append(
                    ThemeFrontendSelection(
                        metadata.theme_id,
                        metadata.name,
                        metadata.version,
                        token_set.appearance,
                        token_set.tokens,
                    )
                )
        selections.sort(
            key=lambda item: (
                item.theme_id.value,
                item.version.parsed.release,
                item.appearance.value,
            )
        )
        return ThemeFrontendCatalog(
            FRONTEND_THEME_CATALOG_SCHEMA_VERSION,
            tuple(selections),
        )


class ThemeFrontendCatalogSerializer:
    """Serialize a transport catalog as a deterministic generated ES module."""

    def serialize(self, catalog: ThemeFrontendCatalog) -> str:
        if not isinstance(catalog, ThemeFrontendCatalog):
            raise ThemeError("Frontend theme serialization requires ThemeFrontendCatalog.")
        payload = {
            "schemaVersion": catalog.schema_version,
            "selections": [self._selection(item) for item in catalog.selections],
        }
        encoded = json.dumps(payload, ensure_ascii=True, indent=2)
        return (
            "// AUTO-GENERATED by E-015.6. Do not edit by hand.\n"
            f"const themeCatalog = {encoded};\n\n"
            "export default themeCatalog;\n"
        )

    @staticmethod
    def _selection(selection: ThemeFrontendSelection) -> dict[str, object]:
        return {
            "themeId": selection.theme_id.value,
            "themeName": selection.theme_name,
            "version": selection.version.value,
            "appearance": selection.appearance.value,
            "tokens": {
                token.name.value: token.value.value for token in selection.tokens
            },
        }


@dataclass(frozen=True, slots=True)
class ThemeFrontendSyncResult:
    """Result of checking or updating the exact frontend catalog module."""

    path: Path
    current: bool
    changed: bool
    selection_count: int


class ThemeFrontendCatalogSynchronizer:
    """Check or atomically update only the fixed frontend catalog module."""

    def __init__(
        self,
        compiler: ThemeFrontendCatalogCompiler | None = None,
        serializer: ThemeFrontendCatalogSerializer | None = None,
    ) -> None:
        self._compiler = compiler or ThemeFrontendCatalogCompiler()
        self._serializer = serializer or ThemeFrontendCatalogSerializer()

    def synchronize(
        self,
        project_root: Path,
        catalog: ThemeCatalog,
        *,
        check: bool = False,
    ) -> ThemeFrontendSyncResult:
        root = project_root.resolve()
        if not root.is_dir():
            raise ThemeError("Frontend theme synchronization requires a project root.")
        target = root / FRONTEND_THEME_CATALOG_PATH
        self._reject_symlinks(root, target)
        document = self._compiler.compile(catalog)
        content = self._serializer.serialize(document)
        encoded = content.encode("utf-8")
        current = self._matches(target, encoded)
        if check or current:
            return ThemeFrontendSyncResult(
                target,
                current,
                False,
                len(document.selections),
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
                temporary = Path(stream.name)
            os.replace(temporary, target)
        except OSError as exc:
            raise ThemeError("Frontend theme catalog could not be synchronized.") from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return ThemeFrontendSyncResult(
            target,
            True,
            True,
            len(document.selections),
        )

    @staticmethod
    def _reject_symlinks(root: Path, target: Path) -> None:
        current = root
        for part in FRONTEND_THEME_CATALOG_PATH.parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ThemeError(
                    "Frontend theme catalog path must not contain symlinks."
                )
        if target.resolve(strict=False) != target:
            raise ThemeError("Frontend theme catalog must remain below the project root.")

    @staticmethod
    def _matches(target: Path, expected: bytes) -> bool:
        if not target.is_file():
            return False
        try:
            if target.stat().st_size > _MAXIMUM_CATALOG_BYTES:
                raise ThemeError("Frontend theme catalog exceeds the size limit.")
            return target.read_bytes() == expected
        except OSError as exc:
            raise ThemeError("Frontend theme catalog could not be read.") from exc


__all__ = [
    "FRONTEND_THEME_CATALOG_PATH",
    "FRONTEND_THEME_CATALOG_SCHEMA_VERSION",
    "ThemeFrontendCatalog",
    "ThemeFrontendCatalogCompiler",
    "ThemeFrontendCatalogSerializer",
    "ThemeFrontendCatalogSynchronizer",
    "ThemeFrontendSelection",
    "ThemeFrontendSyncResult",
]
