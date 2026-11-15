"""
tools/models/video.py — ``Video`` model, an :class:`IStorable`.

Only organizing metadata is persisted. Codec, audio, container and unselected
probe fields are ignored. ``tags`` is a user-managed array, not a copy of file
metadata tags.

Primary-key strategy
--------------------
The scan found **no embedded hash/checksum tag on any file**, so there is no
ready-made content id to reuse. We therefore compute our own ``content_hash`` and
use it as the primary key, while keeping ``path`` as a natural (unique) key:

* ``content_hash`` is stable across moves/renames and lets us detect duplicate
  files stored under different paths — ideal as an identity/primary key.
* ``path`` alone would change whenever a file is moved, so it is kept as a
  secondary natural key rather than the primary key.

Full-file hashing can be slow for large videos, so :func:`compute_content_hash`
supports a fast *partial signature* (size + head + tail) as well as a full hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from tools.storage.interfaces import IStorable

STORAGE_NAME = "videos"
# Head + tail window for the fast partial signature. Benchmarked at 256 KiB
# against 999 real videos under D:\ (see scripts/benchmark_hash.py): it yields the
# exact same de-duplication partition as a 1 MiB window (zero extra collisions)
# while reading 4x less data.
_PARTIAL_CHUNK = 1 << 18  # 256 KiB
# Streaming block size for full-file hashing (kept larger for throughput).
_READ_BLOCK = 1 << 20  # 1 MiB


@dataclass
class Video(IStorable):
    """Metadata for a single video file.

    ``path`` and ``name`` are always required; every other field is optional
    because availability varies by container/codec.
    """

    # =========================================================================
    # RELEVANT — the fields this organizer actually uses to file videos by
    # year/month, directory, name, location, device, and resolution.
    # =========================================================================

    # -- filesystem identity (path & name always required) --
    path: str
    name: str
    content_hash: Optional[str] = None
    directory: Optional[str] = None
    extension: Optional[str] = None
    size_bytes: Optional[int] = None

    # Embedded recording time first; filesystem creation time is the fallback.
    creation_time: Optional[str] = None

    # -- capture device (derived; see tools/video_meta_strategy.py) --
    device: Optional[str] = None  # unified label, e.g. "Apple iPhone 15 Plus", "GoPro", "DJI"
    make: Optional[str] = None
    model: Optional[str] = None

    # -- location: parse ISO-6709 into queryable numbers; raw kept in `location` --
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location: Optional[str] = None  # raw ISO-6709 string (audit/provenance)
    country: Optional[str] = None  # reverse-geocoded from lat/lon (see tools/geocoding.py)
    state: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    # -- resolution / frame rate / duration --
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    duration_sec: Optional[float] = None

    def __post_init__(self) -> None:
        if not isinstance(self.tags, list) or any(not isinstance(tag, str) for tag in self.tags):
            raise TypeError("tags must be an array of strings")

    # -- IStorable contract ----------------------------------------------------

    @property
    def storage_name(self) -> str:
        return STORAGE_NAME

    @property
    def primary_key(self) -> str:
        return "content_hash"

    def indexed_fields(self):
        """Fields the organizer filters/sorts by — indexed for query speed.

        Covers the organizing axes: name, directory, location (lat/lon +
        reverse-geocoded country), capture date (creation_time) and device.
        """
        return ["name", "directory", "latitude", "longitude", "country", "creation_time", "device"]

    def unique_fields(self):
        """``path`` is the natural key: a full file path is unique per file."""
        return ["path"]

    def to_dict(self) -> Dict[str, Any]:
        """Flat mapping of all fields (``None`` values included)."""
        self.__post_init__()
        return asdict(self)

    def __str__(self) -> str:
        res = f"{self.width}x{self.height}" if self.width and self.height else "?"
        dur = f"{self.duration_sec:.1f}s" if self.duration_sec else "?"
        return f"Video(name={self.name!r}, {res}, {dur}, hash={self.content_hash})"

    # -- construction helpers --------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Video":
        """Rebuild a :class:`Video` from a stored row, ignoring unknown keys."""
        known = {f.name for f in fields(cls)}
        values = {k: v for k, v in data.items() if k in known}
        if not values.get("creation_time") and data.get("created_time") is not None:
            values["creation_time"] = datetime.fromtimestamp(
                float(data["created_time"]), UTC
            ).isoformat()
        tags = values.get("tags")
        values["tags"] = (
            json.loads(tags) if isinstance(tags, str) else tags if tags is not None else []
        )
        return cls(**values)


def compute_content_hash(path: str, algorithm: str = "sha256", partial: bool = False) -> str:
    """Compute a content hash for ``path``.

    Args:
        path: File to hash.
        algorithm: Any :mod:`hashlib` algorithm name (default ``sha256``).
        partial: If ``True``, hash only ``size + first 256 KiB + last 256 KiB`` for
            speed. Fast and collision-resistant enough for de-duplication, but
            not a cryptographic guarantee of identical content. If ``False``,
            hash the whole file.

    Returns:
        Hex digest string. For partial hashes the digest is prefixed with
        ``"p:"`` so it is never confused with a full-file digest.
    """
    h = hashlib.new(algorithm)
    size = os.path.getsize(path)
    if partial:
        h.update(str(size).encode())
        with open(path, "rb") as f:
            head = f.read(_PARTIAL_CHUNK)
            h.update(head)
            if size > _PARTIAL_CHUNK * 2:
                f.seek(-_PARTIAL_CHUNK, os.SEEK_END)
                h.update(f.read(_PARTIAL_CHUNK))
        return "p:" + h.hexdigest()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_READ_BLOCK), b""):
            h.update(chunk)
    return h.hexdigest()
