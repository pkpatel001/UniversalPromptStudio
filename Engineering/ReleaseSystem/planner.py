"""Deterministic packaging plans for E-011."""

from __future__ import annotations

from collections.abc import Sequence

from Engineering.core.exceptions import ReleaseError

from .models import PackageFormat, PackageSpec, PackagingPlan, ReleaseContext


class ReleasePlanner:
    """Validate and order local package requests."""

    def plan(
        self,
        context: ReleaseContext,
        formats: Sequence[PackageFormat],
    ) -> PackagingPlan:
        """Return a deterministic plan with one entry per requested format."""

        if not formats:
            raise ReleaseError("At least one package format is required.")
        if len(set(formats)) != len(formats):
            raise ReleaseError("Package formats must be unique.")
        requested = set(formats)
        specs = tuple(PackageSpec(item) for item in PackageFormat if item in requested)
        return PackagingPlan(context.version, specs, dry_run=context.dry_run)
