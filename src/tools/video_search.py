"""
tools/video_search.py — high-level search over stored :class:`Video` records.

Design notes
------------
* **SOLID.** ``VideoSearch`` depends only on the :class:`~tools.storage.interfaces.IStore`
  abstraction, never on a concrete backend, so it works unchanged over the
  SQLite or in-memory store (Dependency Inversion). Each search parameter maps
  to exactly one filter clause via a declarative spec, so adding a new criterion
  means adding one entry — not editing the query logic (Open/Closed).
* **DRY.** A single :meth:`search` builds one combined (AND-ed) query for every
  criterion; the per-field convenience methods and the "skip unset parameters"
  logic are expressed once.
* **Geocoding is abstracted away from querying.** ``country`` is reverse-geocoded
  *at ingest* (see :mod:`tools.geocoding`) and stored as a plain, indexed column,
  so callers simply pass ``country="Greece"`` alongside the other fields — no
  coordinates or geocoder are involved at query time.
"""

from __future__ import annotations

import datetime
from typing import Any, Callable, List, Optional, Sequence, Union

from tools.models.video import STORAGE_NAME, Video
from tools.storage.interfaces import Filter, IStore

DateLike = Union[str, datetime.date, datetime.datetime]


def _year_prefix(value: Union[int, str, datetime.date, datetime.datetime]) -> str:
    """Return the ``"YYYY-"`` prefix used to match a capture year in an ISO timestamp."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return f"{value.year:04d}-"
    return f"{int(value):04d}-"


def _date_prefix(value: DateLike) -> str:
    """Return the ``"YYYY-MM-DD"`` prefix used to match a capture date."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


class VideoSearch:
    """Query stored videos by country, year, date, name and/or path.

    Args:
        store: Any :class:`IStore` holding :class:`Video` rows.
        storage_name: Collection/table name (defaults to ``Video``'s).
    """

    def __init__(self, store: IStore, storage_name: str = STORAGE_NAME) -> None:
        self._store = store
        self._storage = storage_name

    # -- the single, combined query ------------------------------------------- #

    def search(
        self,
        *,
        country: Optional[str] = None,
        year: Optional[Union[int, str, DateLike]] = None,
        date: Optional[DateLike] = None,
        name: Optional[str] = None,
        path: Optional[str] = None,
        exact: bool = False,
        order_by: Optional[str] = "creation_time",
        limit: Optional[int] = None,
    ) -> List[Video]:
        """Return videos matching every supplied criterion (AND) in one query.

        Unset (``None``) criteria are ignored. ``name`` and ``path`` match as
        case-insensitive substrings unless ``exact`` is ``True``. ``year`` and
        ``date`` match the embedded ``creation_time``.
        """
        filters = list(self._build_filters(country, year, date, name, path, exact))
        rows = self._store.query(
            self._storage, filters=filters, order_by=order_by, limit=limit
        )
        return [Video.from_dict(r) for r in rows]

    # -- per-field convenience wrappers (all delegate to `search`) ------------ #

    def by_country(self, country: str, **kwargs: Any) -> List[Video]:
        return self.search(country=country, **kwargs)

    def by_year(self, year: Union[int, str, DateLike], **kwargs: Any) -> List[Video]:
        return self.search(year=year, **kwargs)

    def by_date(self, date: DateLike, **kwargs: Any) -> List[Video]:
        return self.search(date=date, **kwargs)

    def by_name(self, name: str, **kwargs: Any) -> List[Video]:
        return self.search(name=name, **kwargs)

    def by_path(self, path: str, **kwargs: Any) -> List[Video]:
        return self.search(path=path, **kwargs)

    # -- filter construction (declarative: one spec entry per criterion) ------ #

    @staticmethod
    def _build_filters(
        country: Optional[str],
        year: Optional[Union[int, str, DateLike]],
        date: Optional[DateLike],
        name: Optional[str],
        path: Optional[str],
        exact: bool,
    ) -> Sequence[Filter]:
        text_op = "=" if exact else "LIKE"

        def text_value(value: str) -> str:
            return value if exact else f"%{value}%"

        # (raw value, builder). Builders run only for supplied (non-None) values.
        spec: Sequence[tuple[Any, Callable[[Any], Filter]]] = (
            (country, lambda v: ("country", "=", v)),
            (year, lambda v: ("creation_time", "LIKE", f"{_year_prefix(v)}%")),
            (date, lambda v: ("creation_time", "LIKE", f"{_date_prefix(v)}%")),
            (name, lambda v: ("name", text_op, text_value(v))),
            (path, lambda v: ("path", text_op, text_value(v))),
        )
        return [build(value) for value, build in spec if value is not None]
