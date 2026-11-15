# Sampled captioner development

[Back to Thea](../../README.md) | [Usage](README.md)

`sampler.py` owns frame-index selection, letterboxing and chronological contact
sheet construction. `captioner.py` owns context-aware prompts, result models,
the injectable `VisionCaptionBackend` protocol and the existing compatible HTTP
adapter. No model is downloaded or loaded by this package.

The caller supplies model, endpoint, context, video paths and contact-sheet
destination. `SampledCaptioner.caption_video` owns the intermediate image and
removes it in `finally`, including partial files after sampling/backend failures.
It rejects pre-existing destinations and only deletes its own exact output.
`keep_contact_sheet=True` retains an intentionally requested output; otherwise
the returned sample has `image_path=None`, never a dangling path.
Keep retries/inference explicit; do not add replay caching, implicit
downscaling, or a backend-specific dependency to the core sampler.
`src\cli\commands.py` validates CLI/MCP inputs, selects a unique/default or
explicit new JPEG destination, reads an optional environment credential, and
returns the existing dataclass result as a dictionary. It does not change the
sampler, caption prompt or backend's inference behavior.
An explicit CLI/MCP `contact_sheet` path maps to the core retention option;
there is no separate transport-layer cleanup implementation.
The adapter merges existing catalogue metadata before selecting the single
`creation_time` fallback, retains user tags, and checks transient filesystem
size/mtime snapshots for source changes. Those snapshots are not stored.
Prompts receive country/state only; provenance is not a persisted field.

```powershell
python -m pytest src\sampled_captioner\tests -q
```

Tests use synthetic NumPy frames and fake HTTP responses; no model/server is
contacted. Reading real video or calling a vision endpoint is an opt-in
integration task.
