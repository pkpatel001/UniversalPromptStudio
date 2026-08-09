"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation Generator Tests

Tests cover:
- Documentation model creation and immutability
- Project metadata reading
- Structure tree generation
- Configuration reading
- Python AST source analysis
- Markdown rendering
- Documentation generation (determinism, partial failure, output safety)
- CLI integration

===============================================================================
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from Engineering.core.config import (
    Configuration,
    DocumentationConfiguration,
    DocumentationGenerateConfiguration,
    DocumentationOutputConfiguration,
    EngineeringConfiguration,
    LoggingConfiguration,
    ProjectConfiguration,
    PythonConfiguration,
)
from Engineering.core.exceptions import DocumentationGenerationError
from Engineering.core.paths import ProjectPaths
from Engineering.core.validation import ValidationReport
from Engineering.Documentation.analyzer import (
    ClassInfo,
    ConstantInfo,
    FunctionInfo,
    ModuleInfo,
    PythonSourceAnalyzer,
)
from Engineering.Documentation.generator import DocumentationGenerator
from Engineering.Documentation.models import (
    DocumentationDocument,
    DocumentationElement,
    DocumentationElementKind,
    DocumentationMetadata,
    DocumentationReport,
    DocumentationSection,
    FailedDocument,
    GeneratedDocument,
)
from Engineering.Documentation.readers import (
    ConfigurationField,
    ConfigurationReader,
    ConfigurationSection,
    ProjectMetadata,
    ProjectReader,
    StructureNode,
    StructureReader,
)
from Engineering.Documentation.renderer import MarkdownRenderer


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _create_fake_project(
    root: Path,
    *,
    include_api_module: bool = True,
    broken_module: bool = False,
) -> None:
    """
    Create a minimal fake project structure for testing.
    """

    (root / "pyproject.toml").write_text(
        textwrap.dedent("""\
            [project]
            name = "test-project"
            version = "0.1.0"
            description = "A test project"
            license = { text = "MIT" }
            requires-python = ">=3.12"
        """),
        encoding="utf-8",
    )

    (root / "README.md").write_text("# Test Project\n", encoding="utf-8")

    eng = root / "Engineering"
    eng.mkdir()

    config_dir = eng / "config"
    config_dir.mkdir()
    (config_dir / "project.yaml").write_text(
        textwrap.dedent("""\
            project:
              name: "Test Project"
              short_name: "TP"
              company: "Test Corp"
              version: "0.1.0"
              license: "MIT"
              python:
                minimum_version: "3.12"
        """),
        encoding="utf-8",
    )
    (config_dir / "engineering.yaml").write_text(
        textwrap.dedent("""\
            engineering:
              strict_mode: true
              diagnostics: true
              cache:
                enabled: true
              validation:
                enabled: true
              paths:
                verify_on_startup: true
        """),
        encoding="utf-8",
    )
    (config_dir / "documentation.yaml").write_text(
        textwrap.dedent("""\
            documentation:
              enabled: true
              output:
                root: "Engineering/Documentation/Generated"
              generate:
                readme: true
                api: true
                architecture: true
                adrs: false
                project_status: true
                changelog: false
                index: true
                manifests: true
        """),
        encoding="utf-8",
    )
    (config_dir / "logging.yaml").write_text(
        textwrap.dedent("""\
            logging:
              enabled: true
              level: "INFO"
              console: true
              file: false
              directory: "Engineering/Documentation/Logs"
              filename: "engineering.log"
        """),
        encoding="utf-8",
    )

    core = eng / "core"
    core.mkdir()
    (core / "__init__.py").write_text('"""Core package."""\n', encoding="utf-8")
    (core / "version.py").write_text(
        '"""Version information."""\n\nVERSION = "0.1.0"\n',
        encoding="utf-8",
    )

    if include_api_module:
        (core / "config.py").write_text(
            textwrap.dedent("""\
                \"\"\"
                Configuration module.

                Provides project configuration.
                \"\"\"

                from __future__ import annotations


                def get_config() -> str:
                    \"\"\"Return the project configuration.\"\"\"
                    return "config"


                def validate_config(path: str, strict: bool = True) -> bool:
                    \"\"\"Validate a configuration file.\"\"\"
                    return True


                class Configuration:
                    \"\"\"Immutable configuration container.\"\"\"

                    def __init__(self, name: str) -> None:
                        self.name = name


                PROJECT_NAME = "Test Project"
            """),
            encoding="utf-8",
        )

    if broken_module:
        (core / "broken.py").write_text(
            "def broken(:\n",
            encoding="utf-8",
        )

    backend = root / "Backend"
    backend.mkdir()
    (backend / "__init__.py").write_text("", encoding="utf-8")
    (backend / "core").mkdir()
    (backend / "core" / "__init__.py").write_text("", encoding="utf-8")

    docs_dir = root / "Docs"
    docs_dir.mkdir()
    (docs_dir / "00_Project").mkdir()
    (docs_dir / "00_Project" / "PROJECT_VISION.md").write_text(
        "# Project Vision\n", encoding="utf-8"
    )


def _load_config_from_project(root: Path) -> Configuration:
    """
    Load Configuration from a fake project directory.
    """

    from Engineering.core.config import (
        _load_documentation_config,
        _load_engineering_config,
        _load_logging_config,
        _load_project_config,
    )

    config_dir = root / "Engineering" / "config"

    return Configuration(
        project=_load_project_config(config_dir / "project.yaml"),
        engineering=_load_engineering_config(config_dir / "engineering.yaml"),
        documentation=_load_documentation_config(config_dir / "documentation.yaml"),
        logging=_load_logging_config(config_dir / "logging.yaml"),
    )


def _create_paths_for_project(root: Path) -> ProjectPaths:
    """
    Create ProjectPaths pointing at a fake project directory.
    """

    return ProjectPaths(
        root=root,
        engineering=root / "Engineering",
        config=root / "Engineering" / "config",
        backend=root / "Backend",
        frontend=root / "Frontend",
        docs=root / "Docs",
        database=root / "Database",
        plugins=root / "Plugins",
        templates=root / "Templates",
        assets=root / "Assets",
        categories=root / "Categories",
        tests=root / "Tests",
    )


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------


class TestDocumentationElementKind:
    """Tests for DocumentationElementKind."""

    def test_kind_values(self) -> None:
        assert DocumentationElementKind.HEADING.value == "heading"
        assert DocumentationElementKind.PARAGRAPH.value == "paragraph"
        assert DocumentationElementKind.CODE_BLOCK.value == "code_block"
        assert DocumentationElementKind.LIST.value == "list"
        assert DocumentationElementKind.TABLE.value == "table"
        assert DocumentationElementKind.LINK.value == "link"
        assert DocumentationElementKind.SEPARATOR.value == "separator"


class TestDocumentationElement:
    """Tests for DocumentationElement."""

    def test_creation(self) -> None:
        elem = DocumentationElement(
            kind=DocumentationElementKind.PARAGRAPH,
            content="Hello",
        )
        assert elem.kind == DocumentationElementKind.PARAGRAPH
        assert elem.content == "Hello"

    def test_immutable(self) -> None:
        elem = DocumentationElement(
            kind=DocumentationElementKind.PARAGRAPH,
            content="Hello",
        )
        with pytest.raises(AttributeError):
            elem.content = "Changed"  # type: ignore[misc]

    def test_table_element(self) -> None:
        elem = DocumentationElement(
            kind=DocumentationElementKind.TABLE,
            columns=("A", "B"),
            rows=(("1", "2"), ("3", "4")),
        )
        assert elem.columns == ("A", "B")
        assert len(elem.rows) == 2


class TestDocumentationSection:
    """Tests for DocumentationSection."""

    def test_creation(self) -> None:
        section = DocumentationSection(
            title="Test",
            level=2,
            elements=(),
        )
        assert section.title == "Test"
        assert section.level == 2
        assert len(section.elements) == 0

    def test_immutable(self) -> None:
        section = DocumentationSection(title="Test")
        with pytest.raises(AttributeError):
            section.title = "Changed"  # type: ignore[misc]


class TestDocumentationDocument:
    """Tests for DocumentationDocument."""

    def test_creation(self) -> None:
        doc = DocumentationDocument(
            identifier="test",
            title="Test Document",
        )
        assert doc.identifier == "test"
        assert doc.title == "Test Document"

    def test_with_metadata(self) -> None:
        meta = DocumentationMetadata(source="test.py")
        doc = DocumentationDocument(
            identifier="test",
            title="Test",
            metadata=meta,
        )
        assert doc.metadata is not None
        assert doc.metadata.source == "test.py"

    def test_immutable(self) -> None:
        doc = DocumentationDocument(identifier="test", title="Test")
        with pytest.raises(AttributeError):
            doc.identifier = "changed"  # type: ignore[misc]


class TestDocumentationReport:
    """Tests for DocumentationReport."""

    def test_empty_report(self) -> None:
        report = DocumentationReport()
        assert report.success is True
        assert len(report.generated) == 0
        assert len(report.failed) == 0

    def test_summary_success(self) -> None:
        report = DocumentationReport(
            generated=(GeneratedDocument(path="a.md", identifier="a", title="A"),),
        )
        assert "1" in report.summary
        assert "generated" in report.summary

    def test_summary_failure(self) -> None:
        report = DocumentationReport(
            generated=(),
            failed=(FailedDocument(path="a.md", identifier="a", reason="error"),),
            success=False,
        )
        assert "failed" in report.summary

    def test_immutable(self) -> None:
        report = DocumentationReport()
        with pytest.raises(AttributeError):
            report.success = False  # type: ignore[misc]


class TestGeneratedDocument:
    """Tests for GeneratedDocument."""

    def test_creation(self) -> None:
        doc = GeneratedDocument(path="README.md", identifier="readme", title="Overview")
        assert doc.path == "README.md"
        assert doc.identifier == "readme"

    def test_immutable(self) -> None:
        doc = GeneratedDocument(path="a.md", identifier="a", title="A")
        with pytest.raises(AttributeError):
            doc.path = "b.md"  # type: ignore[misc]


class TestFailedDocument:
    """Tests for FailedDocument."""

    def test_creation(self) -> None:
        doc = FailedDocument(path="a.md", identifier="a", reason="parse error")
        assert doc.reason == "parse error"

    def test_immutable(self) -> None:
        doc = FailedDocument(path="a.md", identifier="a", reason="error")
        with pytest.raises(AttributeError):
            doc.reason = "changed"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Project Reader
# -----------------------------------------------------------------------------


class TestProjectReader:
    """Tests for ProjectReader."""

    def test_metadata(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        reader = ProjectReader(paths=paths, config=config)
        meta = reader.metadata()

        assert meta.name == "Test Project"
        assert meta.short_name == "TP"
        assert meta.company == "Test Corp"
        assert meta.version == "0.1.0"
        assert meta.license == "MIT"
        assert meta.python_minimum == "3.12"

    def test_read_pyproject_toml(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        reader = ProjectReader(paths=paths, config=config)
        pyproject = reader.read_pyproject_toml()

        assert pyproject.get("name") == "test-project"
        assert pyproject.get("version") == "0.1.0"

    def test_pyproject_missing(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        (tmp_path / "pyproject.toml").unlink()
        paths = _create_paths_for_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        reader = ProjectReader(paths=paths, config=config)
        assert reader.read_pyproject_toml() == {}


class TestProjectMetadata:
    """Tests for ProjectMetadata."""

    def test_creation(self) -> None:
        meta = ProjectMetadata(
            name="Test",
            short_name="T",
            company="Corp",
            version="1.0",
            license="MIT",
            python_minimum="3.12",
        )
        assert meta.name == "Test"

    def test_immutable(self) -> None:
        meta = ProjectMetadata(
            name="Test",
            short_name="T",
            company="Corp",
            version="1.0",
            license="MIT",
            python_minimum="3.12",
        )
        with pytest.raises(AttributeError):
            meta.name = "Changed"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Structure Reader
# -----------------------------------------------------------------------------


class TestStructureReader:
    """Tests for StructureReader."""

    def test_read_structure(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        reader = StructureReader(paths=paths)
        tree = reader.read(max_depth=2)

        assert tree.is_directory is True
        assert tree.name == tmp_path.name
        assert len(tree.children) > 0

    def test_structure_excludes_cache(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "visible_dir").mkdir()

        paths = _create_paths_for_project(tmp_path)
        reader = StructureReader(paths=paths)
        tree = reader.read(max_depth=1)

        child_names = [c.name for c in tree.children]
        assert "__pycache__" not in child_names
        assert ".git" not in child_names
        assert "visible_dir" in child_names

    def test_structure_sorted(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        (tmp_path / "zzz").mkdir()
        (tmp_path / "aaa").mkdir()
        (tmp_path / "mmm").mkdir()

        paths = _create_paths_for_project(tmp_path)
        reader = StructureReader(paths=paths)
        tree = reader.read(max_depth=1)

        names = [c.name for c in tree.children]
        dirs = [n for n in names if (tmp_path / n).is_dir()]
        files = [n for n in names if not (tmp_path / n).is_dir()]
        assert dirs == sorted(dirs, key=str.lower)
        assert files == sorted(files, key=str.lower)


class TestStructureNode:
    """Tests for StructureNode."""

    def test_creation(self) -> None:
        node = StructureNode(
            name="test",
            is_directory=False,
        )
        assert node.name == "test"
        assert node.is_directory is False
        assert node.children == ()

    def test_immutable(self) -> None:
        node = StructureNode(name="test", is_directory=False)
        with pytest.raises(AttributeError):
            node.name = "changed"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Configuration Reader
# -----------------------------------------------------------------------------


class TestConfigurationReader:
    """Tests for ConfigurationReader."""

    def test_sections(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)

        reader = ConfigurationReader(config=config)
        sections = reader.sections()

        assert len(sections) == 4
        names = [s.name for s in sections]
        assert "Project" in names
        assert "Engineering" in names
        assert "Documentation" in names
        assert "Logging" in names

    def test_project_section_fields(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)

        reader = ConfigurationReader(config=config)
        sections = reader.sections()
        project = next(s for s in sections if s.name == "Project")

        assert project.description != ""
        field_names = [f.name for f in project.fields]
        assert "name" in field_names
        assert "version" in field_names
        assert "license" in field_names

    def test_documentation_section_fields(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)

        reader = ConfigurationReader(config=config)
        sections = reader.sections()
        doc_section = next(s for s in sections if s.name == "Documentation")

        field_names = [f.name for f in doc_section.fields]
        assert "enabled" in field_names
        assert "output.root" in field_names
        assert "generate.api" in field_names

    def test_no_secrets_leaked(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)

        reader = ConfigurationReader(config=config)
        sections = reader.sections()

        all_values = []
        for section in sections:
            for field in section.fields:
                all_values.append(field.value.lower())

        assert "secret" not in " ".join(all_values)
        assert "password" not in " ".join(all_values)
        assert "token" not in " ".join(all_values)


class TestConfigurationField:
    """Tests for ConfigurationField."""

    def test_creation(self) -> None:
        field = ConfigurationField(
            name="test",
            field_type="str",
            value="hello",
        )
        assert field.name == "test"

    def test_immutable(self) -> None:
        field = ConfigurationField(name="test", field_type="str", value="hello")
        with pytest.raises(AttributeError):
            field.name = "changed"  # type: ignore[misc]


class TestConfigurationSection:
    """Tests for ConfigurationSection."""

    def test_creation(self) -> None:
        section = ConfigurationSection(
            name="Test",
            description="A test section",
        )
        assert section.name == "Test"

    def test_immutable(self) -> None:
        section = ConfigurationSection(name="Test", description="desc")
        with pytest.raises(AttributeError):
            section.name = "Changed"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# AST Analyzer
# -----------------------------------------------------------------------------


class TestPythonSourceAnalyzer:
    """Tests for PythonSourceAnalyzer."""

    def test_analyze_module(self, tmp_path: Path) -> None:
        source_file = tmp_path / "test_module.py"
        source_file.write_text(
            textwrap.dedent("""\
                \"\"\"
                Test module.

                This module does testing.
                \"\"\"

                from __future__ import annotations


                def public_func(x: int) -> str:
                    \"\"\"A public function.\"\"\"
                    return str(x)


                def _private_func() -> None:
                    \"\"\"A private function.\"\"\"
                    pass


                class PublicClass:
                    \"\"\"A public class.\"\"\"

                    def public_method(self) -> bool:
                        \"\"\"A public method.\"\"\"
                        return True

                    def _private_method(self) -> None:
                        pass


                MY_CONSTANT = "hello"
            """),
            encoding="utf-8",
        )

        analyzer = PythonSourceAnalyzer()
        info = analyzer.analyze_module(source_file, "test_module")

        assert info.module_name == "test_module"
        assert info.docstring is not None
        assert "Test module" in info.docstring

        func_names = [f.name for f in info.functions]
        assert "public_func" in func_names
        assert "_private_func" not in func_names

        class_names = [c.name for c in info.classes]
        assert "PublicClass" in class_names

        method_names = [m.name for c in info.classes for m in c.methods]
        assert "public_method" in method_names
        assert "_private_method" not in method_names

        const_names = [c.name for c in info.constants]
        assert "MY_CONSTANT" in const_names

    def test_syntax_error(self, tmp_path: Path) -> None:
        source_file = tmp_path / "broken.py"
        source_file.write_text("def broken(:\n", encoding="utf-8")

        analyzer = PythonSourceAnalyzer()
        with pytest.raises(DocumentationGenerationError, match="Syntax error"):
            analyzer.analyze_module(source_file, "broken")

    def test_missing_file(self, tmp_path: Path) -> None:
        source_file = tmp_path / "nonexistent.py"

        analyzer = PythonSourceAnalyzer()
        with pytest.raises(DocumentationGenerationError, match="Failed to read"):
            analyzer.analyze_module(source_file, "nonexistent")

    def test_type_annotations(self, tmp_path: Path) -> None:
        source_file = tmp_path / "typed.py"
        source_file.write_text(
            textwrap.dedent("""\
                from __future__ import annotations


                def typed_func(
                    name: str,
                    count: int = 0,
                    *args: str,
                    verbose: bool = False,
                    **kwargs: int,
                ) -> list[str]:
                    \"\"\"A typed function.\"\"\"
                    return []
            """),
            encoding="utf-8",
        )

        analyzer = PythonSourceAnalyzer()
        info = analyzer.analyze_module(source_file, "typed")

        assert len(info.functions) == 1
        func = info.functions[0]
        assert "name: str" in func.signature
        assert "count: int" in func.signature
        assert "-> list[str]" in func.signature
        assert "verbose: bool = False" in func.signature

    def test_abstract_class(self, tmp_path: Path) -> None:
        source_file = tmp_path / "abstract.py"
        source_file.write_text(
            textwrap.dedent("""\
                from abc import ABC, abstractmethod


                class Base(ABC):
                    \"\"\"An abstract base class.\"\"\"

                    @abstractmethod
                    def do_thing(self) -> None:
                        pass
            """),
            encoding="utf-8",
        )

        analyzer = PythonSourceAnalyzer()
        info = analyzer.analyze_module(source_file, "abstract")

        assert len(info.classes) == 1
        cls = info.classes[0]
        assert cls.name == "Base"
        assert cls.is_abstract is True
        assert len(cls.methods) == 1
        assert cls.methods[0].is_abstract is True

    def test_module_without_docstring(self, tmp_path: Path) -> None:
        source_file = tmp_path / "nodoc.py"
        source_file.write_text(
            textwrap.dedent("""\
                X = 1
            """),
            encoding="utf-8",
        )

        analyzer = PythonSourceAnalyzer()
        info = analyzer.analyze_module(source_file, "nodoc")
        assert info.docstring is None

    def test_annotated_constants(self, tmp_path: Path) -> None:
        source_file = tmp_path / "annotated.py"
        source_file.write_text(
            textwrap.dedent("""\
                from typing import Final

                VERSION: Final[str] = "1.0"
                MAX_SIZE: int = 100
            """),
            encoding="utf-8",
        )

        analyzer = PythonSourceAnalyzer()
        info = analyzer.analyze_module(source_file, "annotated")

        const_names = [c.name for c in info.constants]
        assert "VERSION" in const_names
        assert "MAX_SIZE" in const_names


class TestFunctionInfo:
    """Tests for FunctionInfo."""

    def test_creation(self) -> None:
        func = FunctionInfo(
            name="test",
            signature="test() -> None",
            docstring="A test function.",
        )
        assert func.name == "test"
        assert func.is_method is False

    def test_immutable(self) -> None:
        func = FunctionInfo(name="test", signature="test()", docstring=None)
        with pytest.raises(AttributeError):
            func.name = "changed"  # type: ignore[misc]


class TestClassInfo:
    """Tests for ClassInfo."""

    def test_creation(self) -> None:
        cls = ClassInfo(name="Test", docstring="A class.")
        assert cls.name == "Test"
        assert cls.is_abstract is False

    def test_immutable(self) -> None:
        cls = ClassInfo(name="Test", docstring=None)
        with pytest.raises(AttributeError):
            cls.name = "Changed"  # type: ignore[misc]


class TestConstantInfo:
    """Tests for ConstantInfo."""

    def test_creation(self) -> None:
        const = ConstantInfo(name="X", value="42")
        assert const.name == "X"
        assert const.value == "42"

    def test_immutable(self) -> None:
        const = ConstantInfo(name="X", value="42")
        with pytest.raises(AttributeError):
            const.name = "Y"  # type: ignore[misc]


class TestModuleInfo:
    """Tests for ModuleInfo."""

    def test_creation(self) -> None:
        info = ModuleInfo(
            module_name="test",
            source_path="test.py",
            docstring="Test module.",
        )
        assert info.module_name == "test"

    def test_immutable(self) -> None:
        info = ModuleInfo(module_name="test", source_path="test.py", docstring=None)
        with pytest.raises(AttributeError):
            info.module_name = "changed"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Markdown Renderer
# -----------------------------------------------------------------------------


class TestMarkdownRenderer:
    """Tests for MarkdownRenderer."""

    def test_render_document(self) -> None:
        doc = DocumentationDocument(
            identifier="test",
            title="Test Document",
            description="A test document.",
            metadata=DocumentationMetadata(source="test.py"),
            sections=(
                DocumentationSection(
                    title="Section 1",
                    level=2,
                    elements=(
                        DocumentationElement(
                            kind=DocumentationElementKind.PARAGRAPH,
                            content="Hello world.",
                        ),
                    ),
                ),
            ),
        )

        renderer = MarkdownRenderer()
        output = renderer.render_document(doc)

        assert "AUTO-GENERATED FILE" in output
        assert "Test Document" in output
        assert "A test document." in output
        assert "Section 1" in output
        assert "Hello world." in output
        assert "test.py" in output

    def test_render_code_block(self) -> None:
        section = DocumentationSection(
            title="Code",
            elements=(
                DocumentationElement(
                    kind=DocumentationElementKind.CODE_BLOCK,
                    content="python\ndef hello(): pass",
                ),
            ),
        )

        doc = DocumentationDocument(
            identifier="test",
            title="Test",
            sections=(section,),
        )

        renderer = MarkdownRenderer()
        output = renderer.render_document(doc)
        assert "```python" in output

    def test_render_table(self) -> None:
        section = DocumentationSection(
            title="Table",
            elements=(
                DocumentationElement(
                    kind=DocumentationElementKind.TABLE,
                    columns=("Name", "Value"),
                    rows=(("a", "1"), ("b", "2")),
                ),
            ),
        )

        doc = DocumentationDocument(
            identifier="test",
            title="Test",
            sections=(section,),
        )

        renderer = MarkdownRenderer()
        output = renderer.render_document(doc)
        assert "| Name | Value |" in output
        assert "| a | 1 |" in output
        assert "| b | 2 |" in output

    def test_render_list(self) -> None:
        section = DocumentationSection(
            title="List",
            elements=(
                DocumentationElement(
                    kind=DocumentationElementKind.LIST,
                    items=("Item 1", "Item 2", "Item 3"),
                ),
            ),
        )

        doc = DocumentationDocument(
            identifier="test",
            title="Test",
            sections=(section,),
        )

        renderer = MarkdownRenderer()
        output = renderer.render_document(doc)
        assert "- Item 1" in output
        assert "- Item 2" in output
        assert "- Item 3" in output

    def test_deterministic_output(self) -> None:
        doc = DocumentationDocument(
            identifier="test",
            title="Test",
            sections=(
                DocumentationSection(
                    title="S",
                    elements=(
                        DocumentationElement(
                            kind=DocumentationElementKind.PARAGRAPH,
                            content="Hello",
                        ),
                    ),
                ),
            ),
        )

        renderer = MarkdownRenderer()
        first = renderer.render_document(doc)
        second = renderer.render_document(doc)
        assert first == second

    def test_render_tree(self) -> None:
        tree = StructureNode(
            name="root",
            is_directory=True,
            children=(
                StructureNode(name="file.txt", is_directory=False),
                StructureNode(
                    name="subdir",
                    is_directory=True,
                    children=(
                        StructureNode(name="inner.txt", is_directory=False),
                    ),
                ),
            ),
        )

        renderer = MarkdownRenderer()
        output = renderer.render_tree(tree)
        assert "root/" in output
        assert "file.txt" in output
        assert "subdir/" in output
        assert "inner.txt" in output

    def test_render_empty_document(self) -> None:
        doc = DocumentationDocument(
            identifier="test",
            title="Empty",
        )

        renderer = MarkdownRenderer()
        output = renderer.render_document(doc)
        assert "AUTO-GENERATED FILE" in output
        assert "# Empty" in output


# -----------------------------------------------------------------------------
# Documentation Generator
# -----------------------------------------------------------------------------


class TestDocumentationGenerator:
    """Tests for DocumentationGenerator."""

    def test_generate_full(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        assert report.success is True
        assert len(report.generated) > 0
        assert len(report.failed) == 0
        assert len(report.skipped) == 2  # adrs (disabled) and changelog (not implemented)

        gen_names = [d.identifier for d in report.generated]
        assert "readme" in gen_names
        assert "architecture" in gen_names
        assert "project_status" in gen_names
        assert "index" in gen_names

    def test_generate_writes_files(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        output_root = Path(report.output_root)
        assert output_root.is_dir()

        for doc in report.generated:
            file_path = output_root / doc.path
            assert file_path.is_file(), f"Missing: {doc.path}"
            content = file_path.read_text(encoding="utf-8")
            assert "AUTO-GENERATED FILE" in content

    def test_generate_deterministic(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)

        report1 = generator.generate()
        output_root = Path(report1.output_root)

        first_files: dict[str, str] = {}
        for doc in report1.generated:
            first_files[doc.path] = (output_root / doc.path).read_text(encoding="utf-8")

        report2 = generator.generate()
        for doc in report2.generated:
            content = (output_root / doc.path).read_text(encoding="utf-8")
            assert first_files[doc.path] == content, f"Non-deterministic: {doc.path}"

    def test_generate_disabled(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        config = DocumentationConfiguration(
            enabled=False,
            output=config.documentation.output,
            generate=config.documentation.generate,
        )

        full_config = Configuration(
            project=config.project if hasattr(config, "project") else _load_config_from_project(tmp_path).project,
            engineering=_load_config_from_project(tmp_path).engineering,
            documentation=config,
            logging=_load_config_from_project(tmp_path).logging,
        )

        generator = DocumentationGenerator(config=full_config, paths=paths)
        report = generator.generate()

        assert report.success is True
        assert len(report.generated) == 0
        assert len(report.skipped) > 0

    def test_generate_partial_failure(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path, broken_module=True)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        assert len(report.generated) > 0
        assert len(report.failed) > 0
        assert report.success is False

    def test_generate_report_summary(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        summary = report.summary
        assert "document(s) generated" in summary

    def test_output_root_from_config(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        expected = (tmp_path / "Engineering" / "Documentation" / "Generated").resolve()
        assert generator.output_root == expected

    def test_api_documents_generated(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        api_docs = [d for d in report.generated if d.identifier.startswith("api")]
        assert len(api_docs) > 0

    def test_manifest_generated(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        output_root = Path(report.output_root)
        manifest = output_root / "documentation_manifest.yaml"
        assert manifest.is_file()

        content = manifest.read_text(encoding="utf-8")
        assert "manifest:" in content
        assert "AUTO-GENERATED" in content


class TestDocumentationGeneratorEdgeCases:
    """Edge case tests for DocumentationGenerator."""

    def test_readme_description_from_pyproject(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        doc = generator._build_readme()

        assert "test" in doc.description.lower() or "test" in doc.title.lower()

    def test_architecture_has_structure(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        doc = generator._build_architecture()

        assert len(doc.sections) >= 2

    def test_project_status_has_components(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        doc = generator._build_project_status()

        assert len(doc.sections) >= 2

    def test_index_has_links(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        doc = generator._build_index()

        assert len(doc.sections) >= 1

    def test_api_index_has_modules(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        doc = generator._build_api_index()

        assert len(doc.sections) >= 1

    def test_clean_module_docstring(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        result = generator._clean_module_docstring(
            "===================================================================\n"
            "Test module\n"
            "==================================================================="
        )
        assert "=====" not in result
        assert "Test module" in result

    def test_extract_title_from_markdown(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        title = generator._extract_title_from_markdown("# Hello World\n\nContent")
        assert title == "Hello World"

    def test_extract_title_no_heading(self, tmp_path: Path) -> None:
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        title = generator._extract_title_from_markdown("No heading here")
        assert title == ""


# -----------------------------------------------------------------------------
# CLI Integration
# -----------------------------------------------------------------------------


class TestDocsCLI:
    """Tests for the documentation CLI commands."""

    def test_docs_generate_help(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "validate" in result.output

    def test_docs_generate_subcommand_help(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "generate", "--help"])
        assert result.exit_code == 0
        assert "Generate documentation" in result.output

    def test_docs_validate_subcommand_help(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "validate", "--help"])
        assert result.exit_code == 0
        assert "Validate" in result.output

    def test_docs_generate_runs(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "generate"])
        assert result.exit_code == 0
        assert "documentation" in result.output.lower() or "generated" in result.output.lower()

    def test_docs_validate_without_generate(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["docs", "validate"])
        assert result.exit_code in (0, 1)


# -----------------------------------------------------------------------------
# Integration: Full Generation Cycle
# -----------------------------------------------------------------------------


class TestIntegration:
    """Integration tests for the documentation generator."""

    def test_full_generation_cycle(self, tmp_path: Path) -> None:
        """Test complete generation cycle with real output verification."""
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        assert report.success is True
        assert len(report.generated) > 0

        output_root = Path(report.output_root)

        readme_path = output_root / "README.md"
        assert readme_path.is_file()
        content = readme_path.read_text(encoding="utf-8")
        assert "# Test Project" in content
        assert "AUTO-GENERATED FILE" in content

        arch_path = output_path = output_root / "architecture.md"
        assert arch_path.is_file()
        content = arch_path.read_text(encoding="utf-8")
        assert "Project Structure" in content

        index_path = output_root / "index.md"
        assert index_path.is_file()
        content = index_path.read_text(encoding="utf-8")
        assert "Documentation Index" in content

    def test_regenerate_produces_identical_output(self, tmp_path: Path) -> None:
        """Test that regeneration produces byte-identical output."""
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)

        report1 = generator.generate()
        output_root = Path(report1.output_root)

        first_contents: dict[str, str] = {}
        for doc in report1.generated:
            first_contents[doc.path] = (output_root / doc.path).read_text(encoding="utf-8")

        report2 = generator.generate()
        for doc in report2.generated:
            content = (output_root / doc.path).read_text(encoding="utf-8")
            assert first_contents[doc.path] == content, f"Non-deterministic output: {doc.path}"

    def test_no_absolute_paths_in_output(self, tmp_path: Path) -> None:
        """Test that generated output contains no absolute local paths."""
        _create_fake_project(tmp_path)
        config = _load_config_from_project(tmp_path)
        paths = _create_paths_for_project(tmp_path)

        generator = DocumentationGenerator(config=config, paths=paths)
        report = generator.generate()

        output_root = Path(report.output_root)
        for doc in report.generated:
            content = (output_root / doc.path).read_text(encoding="utf-8")
            assert str(tmp_path) not in content
            assert "C:\\" not in content or "C:\\\\" not in content
