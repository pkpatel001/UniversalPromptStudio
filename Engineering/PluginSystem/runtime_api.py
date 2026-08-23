"""Host-owned lifecycle and contribution contracts for trusted UPS plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from Engineering.core.exceptions import PluginError

from .validation import require_metadata_id


@dataclass(frozen=True, slots=True)
class PluginContribution:
    """One contribution registered by one active plugin."""

    plugin_id: str
    capability_id: str
    contribution_id: str
    value: object


class PluginContributionRegistry:
    """Host-owned registry with plugin-scoped transactional commits."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], PluginContribution] = {}

    def commit(self, contributions: tuple[PluginContribution, ...]) -> None:
        """Atomically commit a plugin's already-validated contributions."""

        keys = tuple(
            (item.plugin_id, item.capability_id, item.contribution_id) for item in contributions
        )
        if len(set(keys)) != len(keys) or any(key in self._items for key in keys):
            raise PluginError("Plugin contribution identity is already registered.")
        self._items.update(zip(keys, contributions, strict=True))

    def remove_plugin(self, plugin_id: str) -> None:
        """Remove every contribution owned by a plugin."""

        self._items = {
            key: item for key, item in self._items.items() if item.plugin_id != plugin_id
        }

    def contributions(self, capability_id: str | None = None) -> tuple[PluginContribution, ...]:
        """Return contributions in deterministic identity order."""

        items = tuple(self._items.values())
        if capability_id is not None:
            items = tuple(item for item in items if item.capability_id == capability_id)
        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.capability_id,
                    item.plugin_id,
                    item.contribution_id,
                ),
            )
        )


class PluginRegistrationContext:
    """Activation-scoped API restricted to manifest-declared capabilities."""

    def __init__(self, plugin_id: str, allowed_capabilities: tuple[str, ...]) -> None:
        self._plugin_id = plugin_id
        self._allowed = frozenset(allowed_capabilities)
        self._pending: dict[tuple[str, str], PluginContribution] = {}
        self._registration_open = True

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    def register(self, capability_id: str, contribution_id: str, value: object) -> None:
        """Stage one contribution for commit after successful activation."""

        if not self._registration_open:
            raise PluginError("Plugin contribution registration is closed.")
        require_metadata_id(capability_id, "Plugin capability")
        require_metadata_id(contribution_id, "Plugin contribution")
        if capability_id not in self._allowed:
            raise PluginError(
                f"Plugin {self._plugin_id} did not declare capability " f"{capability_id!r}."
            )
        key = (capability_id, contribution_id)
        if key in self._pending:
            raise PluginError("Plugin contribution identity is already staged.")
        self._pending[key] = PluginContribution(
            self._plugin_id, capability_id, contribution_id, value
        )

    def staged(self) -> tuple[PluginContribution, ...]:
        """Return pending contributions in deterministic order."""

        return tuple(self._pending[key] for key in sorted(self._pending))

    def close_registration(self) -> None:
        """Prevent registrations after activation returns."""

        self._registration_open = False

    def rollback(self) -> None:
        """Discard every staged contribution."""

        self._registration_open = False
        self._pending.clear()


@runtime_checkable
class RuntimePlugin(Protocol):
    """Structural lifecycle contract implemented by a runtime entry point."""

    def activate(self, context: PluginRegistrationContext) -> None:
        """Register contributions using the activation-scoped context."""

    def deactivate(self, context: PluginRegistrationContext) -> None:
        """Release plugin-owned resources before host cleanup."""


__all__ = [
    "PluginContribution",
    "PluginContributionRegistry",
    "PluginRegistrationContext",
    "RuntimePlugin",
]
