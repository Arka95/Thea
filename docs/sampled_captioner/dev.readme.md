# Sampled captioner development

[Back to Thea](../../README.md) | [Usage](README.md)

`sampler.py` owns frame-index selection, letterboxing and chronological contact
sheet construction. `captioner.py` owns context-aware prompts, result models,
the injectable `VisionCaptionBackend` protocol and the existing compatible HTTP
adapter. No model is downloaded or loaded by this package.

The caller supplies model, endpoint, context, video paths and contact-sheet
output. Keep retries/inference explicit; do not add replay caching, implicit
downscaling, or a backend-specific dependency to the core sampler.
`src\cli\commands.py` validates CLI/MCP inputs, selects a unique/default or
explicit new JPEG destination, reads an optional environment credential, and
returns the existing dataclass result as a dictionary. It does not change the
sampler, caption prompt or backend's inference behavior.

```powershell
python -m pytest src\sampled_captioner\tests -q
```

Tests use synthetic NumPy frames and fake HTTP responses; no model/server is
contacted. Reading real video or calling a vision endpoint is an opt-in
integration task.
