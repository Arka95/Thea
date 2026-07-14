"""
tools/storage/memory_store.py — In-memory dict-based implementation of :class:`IStore`.

Useful for tests and dry runs: no files, no SQL, just nested dictionaries keyed
by ``storage_name`` then primary-key value. Mirrors :class:`SQLiteStore` semantics
(upsert by primary key, dict round-trip) so code can swap backends transparently.
"""

from __future__ import annotations

import copy
import threading
from typing import Any, Dict, List, Optional

from .interfaces import IStorable, IStore


class InMemoryStore(IStore):
    """Thread-safe dictionary-backed store."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def save(self, item: IStorable) -> None:
        data = dict(item.to_dict())
        pk = item.primary_key
        if pk not in data:
            raise ValueError(f"primary key '{pk}' not present in record")
        key = data[pk]
        if key is None:
            raise ValueError(f"primary key '{pk}' must not be None")
        with self._lock:
            table = self._data.setdefault(item.storage_name, {})
            table[key] = copy.deepcopy(data)

    def get(self, storage_name: str, key: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._data.get(storage_name, {}).get(key)
            return copy.deepcopy(row) if row is not None else None

    def all(self, storage_name: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [copy.deepcopy(r) for r in self._data.get(storage_name, {}).values()]

    def __len__(self) -> int:
        with self._lock:
            return sum(len(t) for t in self._data.values())
