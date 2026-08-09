"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Python Source Analyzer

This module provides AST-based analysis of Python source files for
documentation generation. It extracts module-level metadata including
docstrings, public functions, public classes, and type annotations.

The analyzer uses only the Python standard library `ast` module.
It does not perform full static analysis or semantic interpretation.

Public API
----------
from Engineering.Documentation.analyzer import PythonSourceAnalyzer

analyzer = PythonSourceAnalyzer()
module_info = analyzer.analyze_module(path, module_name)

===============================================================================
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from Engineering.core.exceptions import DocumentationGenerationError
from Engineering.core.filesystem import read_text

__all__ = [
    "FunctionInfo",
    "ClassInfo",
    "ConstantInfo",
    "ModuleInfo",
    "PythonSourceAnalyzer",
]


# -----------------------------------------------------------------------------
# Function Info
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    """
    Metadata for a single function or method.
    """

    name: str
    signature: str
    docstring: str | None
    is_method: bool = False
    is_abstract: bool = False
    is_property: bool = False


# -----------------------------------------------------------------------------
# Class Info
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassInfo:
    """
    Metadata for a single class.
    """

    name: str
    docstring: str | None
    bases: tuple[str, ...] = ()
    methods: tuple[FunctionInfo, ...] = ()
    is_abstract: bool = False


# -----------------------------------------------------------------------------
# Constant Info
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConstantInfo:
    """
    Metadata for a module-level constant.
    """

    name: str
    value: str
    type_hint: str | None = None


# -----------------------------------------------------------------------------
# Module Info
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    """
    Metadata for a single Python module.
    """

    module_name: str
    source_path: str
    docstring: str | None
    functions: tuple[FunctionInfo, ...] = ()
    classes: tuple[ClassInfo, ...] = ()
    constants: tuple[ConstantInfo, ...] = ()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_docstring(node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """
    Extract the docstring from an AST node.
    """

    return ast.get_docstring(node, clean=True)


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """
    Build a human-readable function signature string from an AST node.
    """

    args = node.args
    parts: list[str] = []

    all_args = list(args.posonlyargs) + list(args.args)
    defaults_offset = len(all_args) - len(args.defaults)

    for i, arg in enumerate(all_args):
        if arg.arg == "self" or arg.arg == "cls":
            parts.append(arg.arg)
            continue

        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        default_idx = i - defaults_offset
        if default_idx >= 0 and default_idx < len(args.defaults):
            part += f" = {ast.unparse(args.defaults[default_idx])}"
        parts.append(part)

    if args.vararg:
        part = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            part += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(part)

    if args.kwonlyargs:
        for i, arg in enumerate(args.kwonlyargs):
            part = arg.arg
            if arg.annotation:
                part += f": {ast.unparse(arg.annotation)}"
            kw_default = (
                args.kw_defaults[i]
                if i < len(args.kw_defaults)
                else None
            )
            if kw_default is not None:
                part += f" = {ast.unparse(kw_default)}"
            parts.append(part)

    if args.kwarg:
        part = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            part += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(part)

    sig = ", ".join(parts)

    if node.returns:
        return f"{node.name}({sig}) -> {ast.unparse(node.returns)}"

    return f"{node.name}({sig})"


def _is_abstract_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Return True if the function has an @abstractmethod decorator.
    """

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
            return True
    return False


def _is_property_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Return True if the function has a @property decorator.
    """

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "property":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "property":
            return True
    return False


def _is_public(name: str) -> bool:
    """
    Return True if the name is public (does not start with underscore).
    """

    return not name.startswith("_")


# -----------------------------------------------------------------------------
# Source Analyzer
# -----------------------------------------------------------------------------


class PythonSourceAnalyzer:
    """
    Analyzes a Python source file and extracts documentation metadata
    using the standard library AST module.
    """

    def analyze_module(self, path: Path, module_name: str) -> ModuleInfo:
        """
        Analyze a single Python module.

        Parameters
        ----------
        path
            Absolute path to the Python source file.
        module_name
            Dotted module name (e.g. "Engineering.core.config").

        Returns
        -------
        ModuleInfo
            Extracted module metadata.

        Raises
        ------
        DocumentationGenerationError
            If the source file cannot be read or parsed.
        """

        try:
            source = read_text(path)
        except Exception as exc:
            raise DocumentationGenerationError(
                f"Failed to read source file: {path}"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise DocumentationGenerationError(
                f"Syntax error in {path}: {exc.msg} (line {exc.lineno})"
            ) from exc

        docstring = _get_docstring(tree)
        functions = self._extract_functions(tree, is_class_method=False)
        classes = self._extract_classes(tree)
        constants = self._extract_constants(tree)

        return ModuleInfo(
            module_name=module_name,
            source_path=str(path),
            docstring=docstring,
            functions=functions,
            classes=classes,
            constants=constants,
        )

    def _extract_functions(
        self,
        node: ast.Module | ast.ClassDef,
        is_class_method: bool = False,
    ) -> tuple[FunctionInfo, ...]:
        """
        Extract public functions or methods from an AST node.
        """

        functions: list[FunctionInfo] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not _is_public(item.name):
                    continue

                signature = _build_signature(item)
                docstring = _get_docstring(item)

                functions.append(
                    FunctionInfo(
                        name=item.name,
                        signature=signature,
                        docstring=docstring,
                        is_method=is_class_method,
                        is_abstract=_is_abstract_method(item),
                        is_property=_is_property_decorator(item),
                    )
                )

        return tuple(functions)

    def _extract_classes(self, node: ast.Module) -> tuple[ClassInfo, ...]:
        """
        Extract public classes from a module AST.
        """

        classes: list[ClassInfo] = []

        for item in node.body:
            if isinstance(item, ast.ClassDef):
                if not _is_public(item.name):
                    continue

                bases: list[str] = []
                for base in item.bases:
                    bases.append(ast.unparse(base))

                methods = self._extract_functions(item, is_class_method=True)
                docstring = _get_docstring(item)
                is_abstract = _is_abstract_class(item)

                classes.append(
                    ClassInfo(
                        name=item.name,
                        docstring=docstring,
                        bases=tuple(bases),
                        methods=methods,
                        is_abstract=is_abstract,
                    )
                )

        return tuple(classes)

    def _extract_constants(self, node: ast.Module) -> tuple[ConstantInfo, ...]:
        """
        Extract module-level constants.
        """

        constants: list[ConstantInfo] = []

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and _is_public(target.id):
                        value_str = ast.unparse(item.value)
                        if len(value_str) > 80:
                            value_str = value_str[:77] + "..."
                        constants.append(
                            ConstantInfo(
                                name=target.id,
                                value=value_str,
                            )
                        )
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name) and _is_public(item.target.id):
                    value_str = ast.unparse(item.value) if item.value else "..."
                    if len(value_str) > 80:
                        value_str = value_str[:77] + "..."
                    type_hint = ast.unparse(item.annotation) if item.annotation else None
                    constants.append(
                        ConstantInfo(
                            name=item.target.id,
                            value=value_str,
                            type_hint=type_hint,
                        )
                    )

        return tuple(constants)


def _is_abstract_class(node: ast.ClassDef) -> bool:
    """
    Return True if the class has ABC as a base.
    """

    for base in node.bases:
        base_str = ast.unparse(base)
        if "ABC" in base_str:
            return True
    return False
