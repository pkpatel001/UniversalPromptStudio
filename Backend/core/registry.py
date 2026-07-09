"""Registry for providers, services, plugins, and replaceable implementations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RegistryItem(Generic[T]):
    """A named implementation registered with the application."""

    name: str
    implementation: T


class ProviderRegistry(Generic[T]):
    """Type-safe registry for implementations resolved by name."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, name: str, implementation: T) -> None:
        """Register or replace an implementation by name."""

        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Registry item name cannot be empty.")
        self._items[normalized_name] = implementation

    def get(self, name: str) -> T:
        """Return a registered implementation."""

        normalized_name = name.strip().lower()
        try:
            return self._items[normalized_name]
        except KeyError as exc:
            raise KeyError(f"No implementation registered as '{name}'.") from exc

    def names(self) -> tuple[str, ...]:
        """Return registered implementation names."""

        return tuple(sorted(self._items))

    def items(self) -> Iterable[RegistryItem[T]]:
        """Return registry items."""

        for name, implementation in self._items.items():
            yield RegistryItem(name=name, implementation=implementation)

