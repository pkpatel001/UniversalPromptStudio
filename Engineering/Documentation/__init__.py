"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Documentation Subsystem

This package provides deterministic, structured Markdown documentation
generation from the actual Universal Prompt Studio project and its
Engineering Toolkit source.

Generated documentation is derived from authoritative project sources:
* Project configuration
* Repository structure
* Python source metadata (via AST)
* Validation and diagnostic state

Public API
----------
from Engineering.Documentation import DocumentationGenerator

generator = DocumentationGenerator()
report = generator.generate()

===============================================================================
"""

from .analyzer import (
    ClassInfo,
    ConstantInfo,
    FunctionInfo,
    ModuleInfo,
    PythonSourceAnalyzer,
)
from .generator import DocumentationGenerator
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
    ConfigurationField,
    ConfigurationReader,
    ConfigurationSection,
    ProjectMetadata,
    ProjectReader,
    StructureNode,
    StructureReader,
)
from .renderer import MarkdownRenderer

__all__ = [
    "ClassInfo",
    "ConfigurationField",
    "ConfigurationReader",
    "ConfigurationSection",
    "ConstantInfo",
    "DocumentationDocument",
    "DocumentationElement",
    "DocumentationElementKind",
    "DocumentationGenerator",
    "DocumentationMetadata",
    "DocumentationReport",
    "DocumentationSection",
    "FailedDocument",
    "FunctionInfo",
    "GeneratedDocument",
    "MarkdownRenderer",
    "ModuleInfo",
    "ProjectMetadata",
    "ProjectReader",
    "PythonSourceAnalyzer",
    "StructureNode",
    "StructureReader",
]
