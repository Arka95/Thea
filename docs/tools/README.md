# Video Indexing

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

Index source videos without altering them, including offline country lookup and
clearly labelled folder-inferred locations:

```powershell
python -m tools.walkdir "E:\2026 USA" --db "E:\Thea\video_index_2026.sqlite3" --geocode --infer-loc
```

`thea index` and `thea-index` expose the same arguments; MCP tool `index` uses
`root`, `limit`, `db`, `probe`, `geocode` and `infer_loc`. See
[MCP usage](../mcp/README.md). `thea index` prints a JSON summary; the legacy
`thea-index` alias retains its human-readable console summary.

`--db` persists the catalogue across runs; without it, storage remains temporary
and in-memory. The optional positional `LIMIT` still works. `--geocode` and
`--infer-loc` enable metadata probing automatically; `--probe` enables probing
alone. Zero-coordinate placeholders, out-of-range GPS and malformed location
tags are ignored, allowing folder inference when available. Valid embedded GPS
takes precedence over inferred locations. Records are deduplicated by content
hash, so duplicate copies retain one catalogue path.
Offline country lookup uses nearest-city data, so results near borders and
folder-inferred locations are approximate.
