"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Template Renderer

This module provides the rendering abstraction for the Code Generation
framework. It wraps Jinja2 behind a clean interface so that downstream
code never depends on Jinja2 internals.

Rendering is deterministic: the same template source and context
produce the same output, with no timestamps or environment-specific values.

Public API
----------
from Engineering.CodeGeneration.renderer import TemplateRenderer

renderer = TemplateRenderer()
content = renderer.render(template_source, context_dict)

===============================================================================
"""

from __future__ import annotations

from typing import Any

from jinja2 import BaseLoader, StrictUndefined
from jinja2.exceptions import TemplateError as JinjaTemplateError
from jinja2.sandbox import SandboxedEnvironment

from Engineering.core.exceptions import TemplateRenderError

from .models import GenerationContext

__all__ = ["TemplateRenderer"]


class TemplateRenderer:
    """
    Renders template source strings into content using Jinja2.

    The renderer uses ``SandboxedEnvironment`` with ``StrictUndefined``
    to enforce safe, explicit template rendering. No filesystem access,
    path manipulation, or output writing occurs here.

    Rendering is pure: ``source + context → content``.
    """

    def __init__(self) -> None:
        self._environment = SandboxedEnvironment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,
        )

    def render(self, source: str, context: GenerationContext) -> str:
        """
        Render a template source string with a generation context.

        Parameters
        ----------
        source
            Jinja2 template source text.
        context
            GenerationContext providing variables to the template.

        Returns
        -------
        str
            Rendered content.

        Raises
        ------
        TemplateRenderError
            If rendering fails (syntax error, undefined variable, etc.).
        """

        try:
            template = self._environment.from_string(source)
        except JinjaTemplateError as exc:
            raise TemplateRenderError(
                f"Template syntax error: {exc}"
            ) from exc

        rendering_context: dict[str, Any] = {
            "project": context.project,
            "generator": context.generator,
            "artifact": context.artifact,
            "values": context.values,
        }

        try:
            result = template.render(**rendering_context)
        except JinjaTemplateError as exc:
            raise TemplateRenderError(
                f"Template rendering error: {exc}"
            ) from exc

        return result

    def validate_source(self, source: str) -> None:
        """
        Validate that a template source string is syntactically valid
        without rendering.

        Raises
        ------
        TemplateRenderError
            If the template source is not valid Jinja2.
        """

        try:
            self._environment.parse(source)
        except JinjaTemplateError as exc:
            raise TemplateRenderError(
                f"Template syntax error: {exc}"
            ) from exc
