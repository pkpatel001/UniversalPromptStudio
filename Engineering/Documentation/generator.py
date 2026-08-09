"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation Generator

This module orchestrates documentation generation by coordinating
readers, analyzers, and renderers. It is the central service that
produces documentation artifacts from authoritative project sources.

Public API
----------
from Engineering.Documentation.generator import DocumentationGenerator

generator = DocumentationGenerator()
report = generator.generate()

===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from Engineering.core.constants import ENGINEERING_NAME
from Engineering.core.exceptions import DocumentationGenerationError
from Engineering.core.filesystem import ensure_directory, read_text, write_text

from .analyzer import PythonSourceAnalyzer
from .models import (
    DocumentationDocument,
    DocumentationElement,
    DocumentationElementKind,
    DocumentationMetadata,
    DocumentationReport,
    DocumentationSection,
    FailedDocument,
    GeneratedDocument,
)
from .readers import (
    ConfigurationReader,
    ProjectReader,
    StructureNode,
    StructureReader,
)
from .renderer import MarkdownRenderer

if TYPE_CHECKING:
    from Engineering.core.config import Configuration
    from Engineering.core.paths import ProjectPaths

__all__ = ["DocumentationGenerator"]


# -----------------------------------------------------------------------------
# API Module Discovery
# -----------------------------------------------------------------------------


def _discover_core_modules(core_dir: Path) -> list[tuple[str, str]]:
    """
    Discover Python modules in the Engineering core directory.

    Returns a deterministic list of (module_name, relative_source_path)
    tuples for public modules. Private modules (leading underscore) are
    excluded from the public API documentation.
    """

    if not core_dir.is_dir():
        return []

    modules: list[tuple[str, str]] = []
    for path in sorted(core_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        if path.name == "__init__.py":
            continue
        module_name = f"Engineering.core.{path.stem}"
        relative = path.relative_to(core_dir.parent.parent).as_posix()
        modules.append((module_name, relative))
    return modules


# -----------------------------------------------------------------------------
# Documentation Generator
# -----------------------------------------------------------------------------


class DocumentationGenerator:
    """
    Orchestrates documentation generation from the Universal Prompt
    Studio project and Engineering Toolkit source.

    The generator coordinates:
    * Project metadata reading
    * Structure tree generation
    * Configuration documentation
    * Python source analysis (via AST)
    * Markdown rendering
    * File output

    All output is deterministic and reproducible.
    """

    def __init__(
        self,
        config: Configuration | None = None,
        paths: ProjectPaths | None = None,
    ) -> None:
        from Engineering.core.config import get_config
        from Engineering.core.paths import get_paths

        self._config = config if config is not None else get_config()
        self._paths = paths if paths is not None else get_paths()
        self._renderer = MarkdownRenderer()
        self._project_reader = ProjectReader(self._paths, self._config)
        self._structure_reader = StructureReader(self._paths)
        self._config_reader = ConfigurationReader(self._config)
        self._source_analyzer = PythonSourceAnalyzer()

    @property
    def output_root(self) -> Path:
        """
        Return the resolved output root path.
        """

        raw = self._config.documentation.output.root
        return (self._paths.root / raw).resolve()

    def generate(self) -> DocumentationReport:
        """
        Generate all enabled documentation and write to disk.

        Returns
        -------
        DocumentationReport
            Summary of generated, skipped, and failed documents.
        """

        if not self._config.documentation.enabled:
            return DocumentationReport(
                    skipped=(
                        "readme",
                        "api",
                        "architecture",
                        "adrs",
                        "project_status",
                        "changelog",
                        "index",
                        "manifests",
                    ),
                output_root=str(self.output_root),
                success=True,
            )

        generated: list[GeneratedDocument] = []
        skipped: list[str] = []
        failed: list[FailedDocument] = []

        output_root = self.output_root
        ensure_directory(output_root)

        generation_plan = self._build_generation_plan()

        for identifier, filename, builder in generation_plan:
            if builder is None:
                skipped.append(identifier)
                continue

            try:
                document = builder()
                markdown = self._renderer.render_document(document)
                file_path = output_root / filename
                write_text(file_path, markdown)
                generated.append(
                    GeneratedDocument(
                        path=filename,
                        identifier=identifier,
                        title=document.title,
                    )
                )
            except DocumentationGenerationError as exc:
                failed.append(
                    FailedDocument(
                        path=filename,
                        identifier=identifier,
                        reason=str(exc),
                    )
                )
            except Exception as exc:
                failed.append(
                    FailedDocument(
                        path=filename,
                        identifier=identifier,
                        reason=f"Unexpected error: {exc}",
                    )
                )

        self._generate_manifest(output_root, generated, failed)

        return DocumentationReport(
            generated=tuple(generated),
            skipped=tuple(skipped),
            failed=tuple(failed),
            output_root=str(output_root),
            success=len(failed) == 0,
        )

    def _build_generation_plan(
        self,
    ) -> list[tuple[str, str, Callable[[], DocumentationDocument] | None]]:
        """
        Build the ordered list of documents to generate.

        Returns a list of (identifier, filename, builder_function) tuples.
        If builder_function is None, the document is skipped.
        """

        gen = self._config.documentation.generate
        plan: list[
            tuple[str, str, Callable[[], DocumentationDocument] | None]
        ] = []

        plan.append(
            ("readme", "README.md", self._build_readme if gen.readme else None)
        )
        plan.append(
            (
                "architecture",
                "architecture.md",
                self._build_architecture if gen.architecture else None,
            )
        )
        plan.append(
            (
                "project_status",
                "project-status.md",
                self._build_project_status if gen.project_status else None,
            )
        )
        plan.append(("index", "index.md", self._build_index if gen.index else None))

        if gen.api:
            api_modules = _discover_core_modules(
                self._paths.engineering / "core"
            )
            plan.append(
                ("api", "api/README.md", self._build_api_index)
            )

            def _make_api_builder(
                mn: str, sr: str
            ) -> Callable[[], DocumentationDocument]:
                def _builder() -> DocumentationDocument:
                    return self._build_api_module(mn, sr)

                return _builder

            for module_name, source_rel in api_modules:
                filename = module_name.replace(".", "/") + ".md"
                plan.append(
                    (
                        f"api:{module_name}",
                        f"api/{filename}",
                        _make_api_builder(
                            module_name, source_rel
                        ),
                    )
                )
        else:
            plan.append(("api", "api/README.md", None))

        plan.append(("adrs", "adrs.md", self._build_adrs if gen.adrs else None))
        plan.append(("changelog", "changelog.md", None))

        return plan

    # -------------------------------------------------------------------------
    # Document Builders
    # -------------------------------------------------------------------------

    def _build_readme(self) -> DocumentationDocument:
        """
        Build the project README document.
        """

        metadata = self._project_reader.metadata()
        pyproject = self._project_reader.read_pyproject_toml()

        sections: list[DocumentationSection] = []

        description = pyproject.get("description", "")
        if not description:
            description = (
                f"{metadata.name} is an offline-first, AI-agnostic "
                "desktop application for professional prompt engineering, "
                "prompt management, workflow design, template creation, "
                "and AI provider integration."
            )

        sections.append(
            DocumentationSection(
                title="Overview",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=description,
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Project Information",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.TABLE,
                        columns=("Property", "Value"),
                        rows=(
                            ("Name", metadata.name),
                            ("Short Name", metadata.short_name),
                            ("Version", metadata.version),
                            ("License", metadata.license),
                            ("Company", metadata.company),
                            ("Python", f">= {metadata.python_minimum}"),
                        ),
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Engineering Toolkit",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            f"Engineering Toolkit v{metadata.engineering_version}. "
                            "See the [Engineering Toolkit](engineering-toolkit.md) "
                            "documentation for details."
                        ),
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Documentation",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            "This documentation is generated by the Engineering "
                            "Toolkit Documentation Generator."
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.LIST,
                        items=(
                            "[Index](index.md)",
                            "[Architecture](architecture.md)",
                            "[Project Status](project-status.md)",
                            "[API Reference](api/README.md)",
                        ),
                    ),
                ),
            )
        )

        return DocumentationDocument(
            identifier="readme",
            title=metadata.name,
            description="",
            metadata=DocumentationMetadata(
                source="Project configuration, repository structure, and pyproject.toml",
            ),
            sections=tuple(sections),
        )

    def _build_architecture(self) -> DocumentationDocument:
        """
        Build the architecture document.
        """

        metadata = self._project_reader.metadata()
        structure = self._structure_reader.read(max_depth=1)

        sections: list[DocumentationSection] = []

        tree_text = self._renderer.render_tree(structure)
        sections.append(
            DocumentationSection(
                title="Project Structure",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.CODE_BLOCK,
                        content=f"text\n{tree_text}",
                    ),
                ),
            )
        )

        engineering_structure = self._read_engineering_structure()
        eng_tree_text = self._renderer.render_tree(engineering_structure)
        sections.append(
            DocumentationSection(
                title="Engineering Toolkit Structure",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            "The Engineering Toolkit provides infrastructure for "
                            "configuration management, validation, diagnostics, "
                            "documentation generation, and CLI tooling."
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.CODE_BLOCK,
                        content=f"text\n{eng_tree_text}",
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Architecture Layers",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            f"{metadata.name} follows Clean Architecture principles "
                            "with a layered design:"
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.LIST,
                        items=(
                            "Presentation Layer (Frontend — Tauri/Vite)",
                            "Application Layer (Backend/application)",
                            "Domain Layer (Backend/domain)",
                            "Infrastructure (Backend/infrastructure," " Backend/implementations)",
                            "Engineering Toolkit (Engineering/)",
                        ),
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Engineering Toolkit Components",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            "The Engineering Toolkit is organized into the following "
                            "subsystems:"
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.LIST,
                        items=(
                            "Core (Engineering/core/) — Paths,"
                            " filesystem, configuration,"
                            " validation, diagnostics,"
                            " exceptions, constants",
                            "Standards (Engineering/Standards/)"
                            " — Project structure validation rules",
                            "CLI (Engineering/cli/)"
                            " — Command-line interface built with Typer",
                            "Documentation (Engineering/Documentation/)"
                            " — Documentation generation subsystem",
                        ),
                    ),
                ),
            )
        )

        return DocumentationDocument(
            identifier="architecture",
            title="Architecture",
            description="",
            metadata=DocumentationMetadata(
                source="Repository structure and Engineering Toolkit source",
            ),
            sections=tuple(sections),
        )

    def _build_project_status(self) -> DocumentationDocument:
        """
        Build the project status document.
        """

        metadata = self._project_reader.metadata()
        sections: list[DocumentationSection] = []

        sections.append(
            DocumentationSection(
                title="Project Metadata",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.TABLE,
                        columns=("Property", "Value"),
                        rows=(
                            ("Name", metadata.name),
                            ("Version", metadata.version),
                            ("License", metadata.license),
                            ("Python", f">= {metadata.python_minimum}"),
                            ("Engineering Toolkit", f"v{metadata.engineering_version}"),
                        ),
                    ),
                ),
            )
        )

        sections.append(
            DocumentationSection(
                title="Engineering Components",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.TABLE,
                        columns=("Component", "Status"),
                        rows=(
                            ("Core", "Implemented"),
                            ("Standards", "Implemented"),
                            ("CLI", "Implemented"),
                            ("Configuration", "Implemented"),
                            ("Validation", "Implemented"),
                            ("Diagnostics", "Implemented"),
                            ("Documentation Generator", "Implemented"),
                        ),
                    ),
                ),
            )
        )

        return DocumentationDocument(
            identifier="project_status",
            title="Project Status",
            description="",
            metadata=DocumentationMetadata(
                source="Project configuration and Engineering Toolkit source",
            ),
            sections=tuple(sections),
        )

    def _build_index(self) -> DocumentationDocument:
        """
        Build the documentation index document.
        """

        metadata = self._project_reader.metadata()
        sections: list[DocumentationSection] = []

        gen = self._config.documentation.generate

        items: list[str] = []
        if gen.readme:
            items.append(f"[{metadata.name} — Overview](README.md)")
        if gen.architecture:
            items.append("[Architecture](architecture.md)")
        if gen.project_status:
            items.append("[Project Status](project-status.md)")
        if gen.api:
            items.append("[API Reference](api/README.md)")
        items.append("[ADRs](adrs.md)")

        sections.append(
            DocumentationSection(
                title="Documents",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            "This index lists all generated documentation "
                            "produced by the Engineering Toolkit."
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.LIST,
                        items=tuple(items),
                    ),
                ),
            )
        )

        return DocumentationDocument(
            identifier="index",
            title="Documentation Index",
            description="",
            metadata=DocumentationMetadata(
                source="Generated documentation set",
            ),
            sections=tuple(sections),
        )

    def _build_api_index(self) -> DocumentationDocument:
        """
        Build the API reference index document.
        """

        sections: list[DocumentationSection] = []
        items: list[str] = []

        api_modules = _discover_core_modules(self._paths.engineering / "core")

        for module_name, _source_rel in api_modules:
            filename = module_name.replace(".", "/") + ".md"
            items.append(f"[{module_name}]({filename})")

        sections.append(
            DocumentationSection(
                title="Modules",
                level=2,
                elements=(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=(
                            "API documentation for the Engineering Toolkit core modules. "
                            "All public interfaces are documented from source code analysis."
                        ),
                    ),
                    DocumentationElement(
                        kind=DocumentationElementKind.LIST,
                        items=tuple(items),
                    ),
                ),
            )
        )

        return DocumentationDocument(
            identifier="api",
            title="API Reference",
            description="",
            metadata=DocumentationMetadata(
                source="Engineering/core/ Python source (AST analysis)",
            ),
            sections=tuple(sections),
        )

    def _build_api_module(
        self, module_name: str, source_rel: str
    ) -> DocumentationDocument:
        """
        Build API documentation for a single Python module.
        """

        source_path = self._paths.root / source_rel
        module_info = self._source_analyzer.analyze_module(source_path, module_name)

        sections: list[DocumentationSection] = []

        if module_info.docstring:
            clean = self._clean_module_docstring(module_info.docstring)
            if clean:
                sections.append(
                    DocumentationSection(
                        title="Description",
                        level=2,
                        elements=(
                            DocumentationElement(
                                kind=DocumentationElementKind.PARAGRAPH,
                                content=clean,
                            ),
                        ),
                    )
                )

        if module_info.functions:
            func_elements: list[DocumentationElement] = []
            for func in module_info.functions:
                heading = DocumentationElement(
                    kind=DocumentationElementKind.HEADING,
                    content=f"`{func.name}()`",
                    level=3,
                )
                func_elements.append(heading)

                func_elements.append(
                    DocumentationElement(
                        kind=DocumentationElementKind.CODE_BLOCK,
                        content=f"python\n{func.signature}",
                    )
                )

                if func.docstring:
                    func_elements.append(
                        DocumentationElement(
                            kind=DocumentationElementKind.PARAGRAPH,
                            content=self._clean_docstring_first_line(func.docstring),
                        )
                    )

            sections.append(
                DocumentationSection(
                    title="Functions",
                    level=2,
                    elements=tuple(func_elements),
                )
            )

        if module_info.classes:
            class_elements: list[DocumentationElement] = []
            for cls in module_info.classes:
                bases_str = ""
                if cls.bases:
                    bases_str = f" ({', '.join(cls.bases)})"
                heading = DocumentationElement(
                    kind=DocumentationElementKind.HEADING,
                    content=f"`{cls.name}`{bases_str}",
                    level=3,
                )
                class_elements.append(heading)

                if cls.docstring:
                    class_elements.append(
                        DocumentationElement(
                            kind=DocumentationElementKind.PARAGRAPH,
                            content=self._clean_docstring_first_line(cls.docstring),
                        )
                    )

                if cls.methods:
                    for method in cls.methods:
                        class_elements.append(
                            DocumentationElement(
                                kind=DocumentationElementKind.HEADING,
                                content=f"`{method.name}()`",
                                level=4,
                            )
                        )
                        class_elements.append(
                            DocumentationElement(
                                kind=DocumentationElementKind.CODE_BLOCK,
                                content=f"python\n{method.signature}",
                            )
                        )
                        if method.docstring:
                            class_elements.append(
                                DocumentationElement(
                                    kind=DocumentationElementKind.PARAGRAPH,
                                    content=self._clean_docstring_first_line(
                                        method.docstring
                                    ),
                                )
                            )

            sections.append(
                DocumentationSection(
                    title="Classes",
                    level=2,
                    elements=tuple(class_elements),
                )
            )

        if module_info.constants:
            const_elements: list[DocumentationElement] = []
            for const in module_info.constants:
                const_elements.append(
                    DocumentationElement(
                        kind=DocumentationElementKind.PARAGRAPH,
                        content=f"`{const.name}` = `{const.value}`",
                    )
                )

            sections.append(
                DocumentationSection(
                    title="Constants",
                    level=2,
                    elements=tuple(const_elements),
                )
            )

        return DocumentationDocument(
            identifier=f"api:{module_name}",
            title=f"`{module_name}`",
            description="",
            metadata=DocumentationMetadata(
                source=source_rel,
            ),
            sections=tuple(sections),
        )

    def _build_adrs(self) -> DocumentationDocument:
        """
        Build the Architecture Decision Records document.
        """

        adr_dir = self._paths.root / "Docs" / "ADR"
        sections: list[DocumentationSection] = []

        if adr_dir.is_dir():
            adr_files = sorted(adr_dir.glob("*.md"))
            if adr_files:
                items: list[str] = []
                for adr_file in adr_files:
                    content = read_text(adr_file)
                    title = self._extract_title_from_markdown(content)
                    if not title:
                        title = adr_file.stem
                    rel_path = adr_file.relative_to(self._paths.root).as_posix()
                    items.append(f"[{title}]({rel_path})")

                sections.append(
                    DocumentationSection(
                        title="Architecture Decision Records",
                        level=2,
                        elements=(
                            DocumentationElement(
                                kind=DocumentationElementKind.PARAGRAPH,
                                content=(
                                    "Architecture Decision Records (ADRs) document "
                                    "significant architectural decisions made in the project."
                                ),
                            ),
                            DocumentationElement(
                                kind=DocumentationElementKind.LIST,
                                items=tuple(items),
                            ),
                        ),
                    )
                )

        if not sections:
            sections.append(
                DocumentationSection(
                    title="Architecture Decision Records",
                    level=2,
                    elements=(
                        DocumentationElement(
                            kind=DocumentationElementKind.PARAGRAPH,
                            content="No architecture decision records found.",
                        ),
                    ),
                )
            )

        return DocumentationDocument(
            identifier="adrs",
            title="Architecture Decision Records",
            description="",
            metadata=DocumentationMetadata(
                source="Docs/ADR/",
            ),
            sections=tuple(sections),
        )

    # -------------------------------------------------------------------------
    # Manifest
    # -------------------------------------------------------------------------

    def _generate_manifest(
        self,
        output_root: Path,
        generated: list[GeneratedDocument],
        failed: list[FailedDocument],
    ) -> None:
        """
        Generate the documentation manifest YAML file.
        """

        gen = self._config.documentation.generate
        if not gen.manifests:
            return

        lines: list[str] = []
        lines.append(
            "# =============================================================================="
        )
        lines.append("# Universal Prompt Studio")
        lines.append("# Engineering Toolkit")
        lines.append("#")
        lines.append("# Documentation Manifest")
        lines.append("#")
        lines.append("# AUTO-GENERATED FILE — DO NOT EDIT MANUALLY.")
        lines.append(
            "# =============================================================================="
        )
        lines.append("")
        lines.append("manifest:")
        lines.append(f'  generated_by: "{ENGINEERING_NAME}"')
        lines.append(f'  output_root: "{self._config.documentation.output.root}"')
        lines.append("")
        lines.append("  documents:")

        for doc in generated:
            lines.append(f'    - identifier: "{doc.identifier}"')
            lines.append(f'      path: "{doc.path}"')
            lines.append(f'      title: "{doc.title}"')

        if failed:
            lines.append("")
            lines.append("  failed:")

            for fail in failed:
                lines.append(f'    - identifier: "{fail.identifier}"')
                lines.append(f'      path: "{fail.path}"')
                lines.append(f'      reason: "{fail.reason}"')
        manifest_path = output_root / "documentation_manifest.yaml"
        write_text(manifest_path, "\n".join(lines) + "\n")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _read_engineering_structure(self) -> StructureNode:
        """
        Read the Engineering directory structure.
        """

        eng_dir = self._paths.engineering
        if not eng_dir.is_dir():
            return StructureNode(
                name="Engineering",
                is_directory=True,
                depth=0,
            )

        return self._structure_reader._read_node(
            eng_dir, depth=0, max_depth=2
        )

    def _clean_module_docstring(self, docstring: str) -> str:
        """
        Clean a module docstring for documentation rendering.
        """

        lines = docstring.split("\n")
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("=") and len(stripped) > 10:
                continue
            cleaned.append(stripped)

        result = "\n".join(cleaned).strip()
        return result

    def _clean_docstring_first_line(self, docstring: str) -> str:
        """
        Extract and clean the first meaningful line from a docstring.
        """

        for line in docstring.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("="):
                return stripped
        return ""

    def _extract_title_from_markdown(self, content: str) -> str:
        """
        Extract the first heading from a Markdown file.
        """

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return ""
