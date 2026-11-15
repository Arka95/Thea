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

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# A single filter clause: (field, operator, value). Operators are a small, safe
# SQL-compatible set shared by every store so query behaviour is backend-neutral.
Filter = Tuple[str, str, Any]

QUERY_OPS = {"=", "!=", "<", "<=", ">", ">=", "LIKE"}


def _like_to_regex(pattern: str) -> "re.Pattern[str]":
    """Translate a SQL ``LIKE`` pattern (``%`` and ``_``) to a regex.

    Case-insensitive, matching SQLite's default ASCII ``LIKE`` semantics so the
    in-memory fallback and the SQLite backend agree.
    """
    parts = ["(?is)^"]
    for ch in pattern:
        if ch == "%":
            parts.append(".*")
        elif ch == "_":
            parts.append(".")
        else:
            parts.append(re.escape(ch))
    parts.append("$")
    return re.compile("".join(parts))


def match_filter(value: Any, op: str, target: Any) -> bool:
    """Evaluate one ``(op, target)`` clause against ``value`` (Python fallback)."""
    if op == "LIKE":
        return value is not None and _like_to_regex(str(target)).match(str(value)) is not None
    if value is None or target is None:
        if op == "=":
            return value is target
        if op == "!=":
            return value is not target
        return False
    if op == "=":
        return value == target
    if op == "!=":
        return value != target
    if op == "<":
        return value < target
    if op == "<=":
        return value <= target
    if op == ">":
        return value > target
    if op == ">=":
        return value >= target
    raise ValueError(f"unsupported operator: {op!r}")


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

    def indexed_fields(self) -> List[str]:
        """Field names that should be secondary-indexed for query performance.

        Returned fields that are not (yet) columns are ignored by the store, so
        it is safe to list optional fields. Default: no secondary indexes.
        """
        return []

    def unique_fields(self) -> List[str]:
        """Field names that should carry a UNIQUE index (natural keys).

        Like :meth:`indexed_fields`, unknown fields are ignored by the store.
        A field listed here need not also appear in :meth:`indexed_fields` — a
        unique index already serves lookups. Under an upsert store that uses
        ``INSERT OR REPLACE``, a UNIQUE field also acts as an alternative upsert
        key: saving a record whose unique value already exists replaces the
        prior row rather than raising. Default: none.
        """
        return []


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

    def query(
        self,
        storage_name: str,
        filters: Optional[Sequence[Filter]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return rows matching every filter (AND), optionally sorted/limited.

        ``filters`` is a sequence of ``(field, operator, value)`` clauses using
        :data:`QUERY_OPS`. This default implementation filters :meth:`all` in
        Python so *any* store is queryable; backends may override for indexed
        access. Rows missing the sort key are ordered last.
        """
        rows = self.all(storage_name)
        if filters:
            rows = [r for r in rows
                    if all(match_filter(r.get(f), op, val) for f, op, val in filters)]
        if order_by:
            present = [r for r in rows if r.get(order_by) is not None]
            missing = [r for r in rows if r.get(order_by) is None]
            present.sort(key=lambda r: r.get(order_by))
            rows = present + missing
        if limit is not None:
            rows = rows[:max(0, limit)]
        return rows
