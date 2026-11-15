"""
tools/storage/sqlite_store.py — SQLite implementation of :class:`IStore`.

Design goals (per requirements):
* **Nonrestrictive** — no auth, no rigid schema. Tables are created lazily and
  evolve automatically: whenever a storable introduces a new field, a matching
  column is added on the fly (``ALTER TABLE ... ADD COLUMN``). SQLite's dynamic
  typing keeps this simple.
* **Queryable** — every storable field becomes a real column, so the data can be
  queried with ordinary SQL. Non-scalar values (list/dict) are JSON-encoded so
  they still live in a column and can be read back losslessly.
* **Idempotent** — rows are upserted by primary key (``INSERT OR REPLACE``), so
  re-scanning the same file updates its row instead of duplicating it.
* **SOLID** — depends only on the :class:`IStorable` abstraction; it never needs
  to know a concrete type such as ``Video``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from .interfaces import IStorable, IStore, QUERY_OPS

_SCALAR = (str, int, float, bool, type(None))


def _encode(value: Any) -> Any:
    """Encode a value for storage. Scalars pass through; containers -> JSON."""
    if isinstance(value, _SCALAR):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _decode(value: Any) -> Any:
    """Best-effort decode of a stored value. JSON containers are parsed back."""
    if isinstance(value, str) and value[:1] in ("[", "{"):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def _quote_ident(name: str) -> str:
    """Safely quote a SQL identifier (table/column name)."""
    return '"' + name.replace('"', '""') + '"'


class SQLiteStore(IStore):
    """A schema-evolving, thread-safe SQLite store for :class:`IStorable` objects.

    Args:
        path: Database file path, or ``":memory:"`` for an in-memory database.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        # check_same_thread=False + a lock lets the multithreaded walker share
        # one connection safely (SQLite is single-writer; the lock serializes).
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        # WAL improves read/write concurrency; harmless for :memory: (ignored).
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        self._columns: Dict[str, set] = {}
        self._indexes: Dict[str, set] = {}

    # -- IStore ----------------------------------------------------------------

    def save(self, item: IStorable) -> None:
        data = dict(item.to_dict())
        table = item.storage_name
        pk = item.primary_key

        if pk not in data:
            raise ValueError(f"primary key '{pk}' not present in {table} record")
        if data[pk] is None:
            raise ValueError(f"primary key '{pk}' must not be None for {table}")

        with self._lock:
            self._ensure_table(table, pk)
            self._ensure_columns(table, data.keys())
            self._ensure_indexes(table, item.indexed_fields())
            self._ensure_indexes(table, item.unique_fields(), unique=True)

            cols = list(data.keys())
            placeholders = ", ".join("?" for _ in cols)
            col_sql = ", ".join(_quote_ident(c) for c in cols)
            values = [_encode(data[c]) for c in cols]
            self._conn.execute(
                f"INSERT OR REPLACE INTO {_quote_ident(table)} "
                f"({col_sql}) VALUES ({placeholders})",
                values,
            )
            self._conn.commit()

    def get(self, storage_name: str, key: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._table_exists(storage_name):
                return None
            pk = self._primary_key_of(storage_name)
            cur = self._conn.execute(
                f"SELECT * FROM {_quote_ident(storage_name)} "
                f"WHERE {_quote_ident(pk)} = ?",
                (key,),
            )
            row = cur.fetchone()
            return self._row_to_dict(row) if row is not None else None

    def all(self, storage_name: str) -> List[Dict[str, Any]]:
        with self._lock:
            if not self._table_exists(storage_name):
                return []
            cur = self._conn.execute(f"SELECT * FROM {_quote_ident(storage_name)}")
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def query(self, storage_name, filters=None, order_by=None, limit=None):
        """Indexed SQL implementation of :meth:`IStore.query`.

        Filters compile to a parameterized ``WHERE`` (values are always bound,
        never interpolated); the secondary indexes created for the storable's
        fields let SQLite satisfy the common lookups without a full scan. A
        filter on an unknown column yields no rows (nothing can match it).
        """
        with self._lock:
            if not self._table_exists(storage_name):
                return []
            columns = self._fetch_columns(storage_name)

            where, params = [], []
            for field, op, value in (filters or []):
                op_upper = op.upper()
                if op_upper not in QUERY_OPS:
                    raise ValueError(f"unsupported operator: {op!r}")
                if field not in columns:
                    return []
                where.append(f"{_quote_ident(field)} {op_upper} ?")
                params.append(value)

            sql = f"SELECT * FROM {_quote_ident(storage_name)}"
            if where:
                sql += " WHERE " + " AND ".join(where)
            if order_by and order_by in columns:
                sql += f" ORDER BY {_quote_ident(order_by)}"
            if limit is not None:
                sql += " LIMIT ?"
                params.append(int(limit))

            cur = self._conn.execute(sql, params)
            return [self._row_to_dict(r) for r in cur.fetchall()]

    # -- lifecycle -------------------------------------------------------------

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- internals -------------------------------------------------------------

    def _ensure_table(self, table: str, pk: str) -> None:
        if self._table_exists(table):
            self._columns.setdefault(table, self._fetch_columns(table))
            return
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_quote_ident(table)} "
            f"({_quote_ident(pk)} PRIMARY KEY)"
        )
        self._conn.commit()
        self._columns[table] = {pk}

    def _ensure_columns(self, table: str, keys) -> None:
        known = self._columns.setdefault(table, self._fetch_columns(table))
        for col in keys:
            if col not in known:
                self._conn.execute(
                    f"ALTER TABLE {_quote_ident(table)} ADD COLUMN {_quote_ident(col)}"
                )
                known.add(col)
        self._conn.commit()

    def _ensure_indexes(self, table: str, fields, unique: bool = False) -> None:
        """Create a secondary index per field, idempotently.

        Only fields that already exist as columns are indexed; unknown fields are
        skipped so storables may list optional fields safely. Indexes are created
        with ``IF NOT EXISTS`` and tracked in-process to avoid redundant DDL. When
        ``unique`` is ``True`` a ``UNIQUE`` index is created (natural-key fields).
        """
        if not fields:
            return
        columns = self._columns.setdefault(table, self._fetch_columns(table))
        created = self._indexes.setdefault(table, set())
        kind = "UNIQUE INDEX" if unique else "INDEX"
        prefix = "uix" if unique else "idx"
        changed = False
        for field in fields:
            marker = (field, unique)
            if field not in columns or marker in created:
                continue
            index_name = f"{prefix}_{table}_{field}"
            self._conn.execute(
                f"CREATE {kind} IF NOT EXISTS {_quote_ident(index_name)} "
                f"ON {_quote_ident(table)} ({_quote_ident(field)})"
            )
            created.add(marker)
            changed = True
        if changed:
            self._conn.commit()

    def _table_exists(self, table: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        return cur.fetchone() is not None

    def _fetch_columns(self, table: str) -> set:
        cur = self._conn.execute(f"PRAGMA table_info({_quote_ident(table)})")
        return {r["name"] for r in cur.fetchall()}

    def _primary_key_of(self, table: str) -> str:
        cur = self._conn.execute(f"PRAGMA table_info({_quote_ident(table)})")
        for r in cur.fetchall():
            if r["pk"]:
                return r["name"]
        return "rowid"

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {k: _decode(row[k]) for k in row.keys()}
