"""
tools/storage/interfaces.py — Storage abstractions.

Defines the two core contracts:

* ``IStorable`` — anything that can be persisted by an ``IStore``. Every storable
  exposes a dict representation (``to_dict``) and a human-readable string
  (``__str__``), plus enough identity information (``storage_name`` and
  ``primary_key``) for a *generic* store to persist it without knowing its
  concrete type.

* ``IStore`` — a store that can ``save`` any ``IStorable`` and read it back.

These are pure abstractions (Dependency Inversion): high-level code depends on
``IStore``/``IStorable``, never on a concrete backend such as SQLite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional


class IStorable(ABC):
    """Contract for any object that can be stored in an :class:`IStore`.

    A storable must be able to describe itself as a flat ``dict`` (its column
    values) and as a readable string. It must also declare *where* it belongs
    (``storage_name`` — e.g. a table/collection name) and *how it is identified*
    (``primary_key`` — the name of the key field within :meth:`to_dict`).
    """

    @property
    @abstractmethod
    def storage_name(self) -> str:
        """Logical collection/table name this object is stored under."""

    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Name of the field in :meth:`to_dict` that uniquely identifies the row."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Return a flat mapping of field name -> value for persistence."""

    @abstractmethod
    def __str__(self) -> str:  # noqa: D105 - human readable representation
        ...

    def key_value(self) -> Any:
        """Value of the primary-key field for this instance."""
        return self.to_dict().get(self.primary_key)


class IStore(ABC):
    """Contract for a persistence backend.

    The essential operation is :meth:`save`. Read helpers (:meth:`get`,
    :meth:`all`) are provided so callers can round-trip data back out of the
    store (e.g. reload persisted :class:`IStorable` rows).
    """

    @abstractmethod
    def save(self, item: IStorable) -> None:
        """Persist a single storable (insert or replace by primary key)."""

    @abstractmethod
    def get(self, storage_name: str, key: Any) -> Optional[Dict[str, Any]]:
        """Return the stored row for ``key`` as a dict, or ``None`` if absent."""

    @abstractmethod
    def all(self, storage_name: str) -> List[Dict[str, Any]]:
        """Return all stored rows under ``storage_name`` as dicts."""

    def save_many(self, items: Iterable[IStorable]) -> None:
        """Persist an iterable of storables. Default: save one by one."""
        for item in items:
            self.save(item)
