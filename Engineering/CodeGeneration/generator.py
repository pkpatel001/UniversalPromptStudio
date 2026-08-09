"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Generator Abstraction

This module defines the Generator ABC and a built-in StaticGenerator
that plans from explicit artifact specifications.

Specialized generators (E-009+) will implement the Generator ABC and
delegate to the GenerationEngine for execution.

Public API
----------
from Engineering.CodeGeneration.generator import Generator, StaticGenerator

===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .models import GenerationPlan, GenerationRequest
from .planner import GenerationPlanner

__all__ = ["Generator", "StaticGenerator"]


class Generator(ABC):
    """
    Abstract base class for code generators.

    Each generator has an identifier and can produce a ``GenerationPlan``
    from a ``GenerationRequest``. The engine is responsible for executing
    the plan; generators only describe what should be produced.
    """

    @property
    @abstractmethod
    def generator_id(self) -> str:
        """Unique identifier for this generator."""

    @abstractmethod
    def plan(self, request: GenerationRequest, project_root: Path) -> GenerationPlan:
        """
        Produce a validated generation plan from a request.

        Parameters
        ----------
        request
            The generation request.
        project_root
            Absolute path to the project root.

        Returns
        -------
        GenerationPlan
            Validated plan describing artifacts to produce.
        """


class StaticGenerator(Generator):
    """
    A framework-level generator that plans directly from a request's
    artifact specifications.

    This generator uses ``GenerationPlanner`` for structural validation
    and serves as the default implementation for framework testing and
    demonstration.
    """

    _GENERATOR_ID = "static"

    def __init__(self, planner: GenerationPlanner | None = None) -> None:
        self._planner = planner or GenerationPlanner()

    @property
    def generator_id(self) -> str:
        return self._GENERATOR_ID

    def plan(self, request: GenerationRequest, project_root: Path) -> GenerationPlan:
        """
        Plan artifacts from the request's explicit specification.

        Delegates to ``GenerationPlanner`` for structural validation.
        """

        return self._planner.plan(request, project_root)
