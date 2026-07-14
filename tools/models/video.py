"""
tools/models/video.py — ``Video`` model, an :class:`IStorable`.

Field selection was driven by a real scan of 999 videos under ``D:\\`` (see
``tools/_explore_metadata.py``). The columns below are the de-duplicated union of
metadata that videos actually carry, grouped into: filesystem identity, container
/ format, stream counts, primary video stream, primary audio stream, and common
container tags. ``raw_metadata`` is a catch-all JSON blob so nothing probed is
ever lost.

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
from typing import Any, Dict, Optional

from tools.storage.interfaces import IStorable

STORAGE_NAME = "videos"
_PARTIAL_CHUNK = 1 << 20  # 1 MiB head + tail for the fast signature


@dataclass
class Video(IStorable):
    """Metadata for a single video file.

    ``path`` and ``name`` are always required; every other field is optional
    because availability varies by container/codec.
    """

    # --- filesystem identity (path & name always required) ---
    path: str
    name: str
    content_hash: Optional[str] = None
    directory: Optional[str] = None
    extension: Optional[str] = None
    size_bytes: Optional[int] = None
    modified_time: Optional[float] = None
    created_time: Optional[float] = None

    # --- container / format ---
    format_name: Optional[str] = None
    format_long_name: Optional[str] = None
    duration_sec: Optional[float] = None
    bit_rate: Optional[int] = None
    nb_streams: Optional[int] = None
    start_time: Optional[float] = None
    probe_score: Optional[int] = None

    # --- stream counts ---
    video_stream_count: Optional[int] = None
    audio_stream_count: Optional[int] = None
    subtitle_stream_count: Optional[int] = None
    data_stream_count: Optional[int] = None

    # --- primary video stream ---
    video_codec: Optional[str] = None
    video_codec_long: Optional[str] = None
    video_profile: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    coded_width: Optional[int] = None
    coded_height: Optional[int] = None
    pix_fmt: Optional[str] = None
    level: Optional[int] = None
    video_bit_rate: Optional[int] = None
    fps: Optional[float] = None
    avg_frame_rate: Optional[str] = None
    r_frame_rate: Optional[str] = None
    nb_frames: Optional[int] = None
    has_b_frames: Optional[int] = None
    sample_aspect_ratio: Optional[str] = None
    display_aspect_ratio: Optional[str] = None
    color_range: Optional[str] = None
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    field_order: Optional[str] = None
    bits_per_raw_sample: Optional[int] = None

    # --- primary audio stream ---
    audio_codec: Optional[str] = None
    audio_codec_long: Optional[str] = None
    audio_profile: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    channel_layout: Optional[str] = None
    sample_fmt: Optional[str] = None
    audio_bit_rate: Optional[int] = None
    audio_bits_per_sample: Optional[int] = None

    # --- common container tags ---
    creation_time: Optional[str] = None
    major_brand: Optional[str] = None
    location: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    encoder: Optional[str] = None
    android_version: Optional[str] = None
    capture_fps: Optional[str] = None

    # --- catch-all: full probed metadata as JSON (nothing lost) ---
    raw_metadata: Optional[Dict[str, Any]] = None

    # -- IStorable contract ----------------------------------------------------

    @property
    def storage_name(self) -> str:
        return STORAGE_NAME

    @property
    def primary_key(self) -> str:
        return "content_hash"

    def to_dict(self) -> Dict[str, Any]:
        """Flat mapping of all fields (``None`` values included)."""
        return asdict(self)

    def __str__(self) -> str:
        res = f"{self.width}x{self.height}" if self.width and self.height else "?"
        dur = f"{self.duration_sec:.1f}s" if self.duration_sec else "?"
        codec = self.video_codec or "?"
        return f"Video(name={self.name!r}, {res}, {codec}, {dur}, hash={self.content_hash})"

    # -- construction helpers --------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Video":
        """Rebuild a :class:`Video` from a stored row, ignoring unknown keys."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def compute_content_hash(path: str, algorithm: str = "sha256", partial: bool = False) -> str:
    """Compute a content hash for ``path``.

    Args:
        path: File to hash.
        algorithm: Any :mod:`hashlib` algorithm name (default ``sha256``).
        partial: If ``True``, hash only ``size + first 1 MiB + last 1 MiB`` for
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
        for chunk in iter(lambda: f.read(_PARTIAL_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
