"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Generator Registry

This module provides a minimal registry for mapping generator identifiers
to Generator implementations. The registry is intentionally minimal in
E-008; specialized generators (E-009+) will populate it.

Public API
----------
from Engineering.CodeGeneration.registry import GeneratorRegistry

registry = GeneratorRegistry()
registry.register(static_generator)
gen = registry.resolve("static")

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from Engineering.core.exceptions import CodeGenerationError
from Engineering.core.paths import get_paths

from .generator import Generator
from .models import GenerationPlan, GenerationRequest

__all__ = ["GeneratorRegistry"]


class GeneratorRegistry:
    """
    Maps generator identifiers to Generator implementations.

    The registry is a thin lookup layer. It does not manage lifecycle,
    dependency injection, or template repositories.
    """

    def __init__(self) -> None:
        self._generators: dict[str, Generator] = {}

    def register(self, generator: Generator) -> None:
        """
        Register a generator.

        Parameters
        ----------
        generator
            Generator to register. Its ``generator_id`` is used as the key.

        Raises
        ------
        CodeGenerationError
            If a generator with this ID is already registered.
        """

        gid = generator.generator_id
        if gid in self._generators:
            raise CodeGenerationError(
                f"Generator already registered: {gid!r}"
            )
        self._generators[gid] = generator

    def resolve(self, generator_id: str) -> Generator:
        """
        Look up a generator by identifier.

        Raises
        ------
        CodeGenerationError
            If no generator is registered with this ID.
        """

        if generator_id not in self._generators:
            raise CodeGenerationError(
                f"No generator registered with id: {generator_id!r}. "
                f"Available: {', '.join(sorted(self._generators)) or '(none)'}"
            )
        return self._generators[generator_id]

    def contains(self, generator_id: str) -> bool:
        """Return True if a generator with this ID is registered."""

        return generator_id in self._generators

    def generator_ids(self) -> tuple[str, ...]:
        """Return all registered generator identifiers, sorted."""

        return tuple(sorted(self._generators.keys()))

    def plan(
        self,
        request: GenerationRequest,
        project_root: Path | None = None,
    ) -> GenerationPlan:
        """
        Convenience method: resolve the generator and produce a plan.

        Parameters
        ----------
        request
            The generation request.
        project_root
            Project root path. If None, discovered automatically.

        Returns
        -------
        GenerationPlan

        Raises
        ------
        CodeGenerationError
            If the generator is not registered.
        """


        root = project_root if project_root is not None else get_paths().root
        generator = self.resolve(request.generator_id)
        return generator.plan(request, root)
