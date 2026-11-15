# Video catalogue development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\tools` is application code, not an automation directory. Preserve its
existing public import names.

| Owner | Responsibility |
|-------|----------------|
| `models\video.py` | Video metadata entity and content identity |
| `storage` | Store/filter interfaces and in-memory/SQLite implementations |
| `video_meta_strategy.py` | ffprobe execution and device/location/metadata extraction |
| `geocoding.py` | Injectable reverse geocoder and place gazetteer |
| `video_search.py` | Catalogue queries over store implementations |
| `catalogue.py` | Atomic canonical schema migration, imports, safe metadata merging, descriptions, locale enrichment and ranked text search |
| `walkdir.py` | Directory discovery, metadata population, storage and indexing CLI |

`thea-index` and `python -m tools.walkdir` call the same `main(argv)` function.
Both use configured `data_dir\video-index.sqlite3`, as do caption/import/search.
Generic stores remain injectable for unit tests and library consumers.
No Thea MCP server or model runtime is created by importing these packages.

`index_videos` validates its root and returns a per-run `scan` separately from
the whole store's `distinct` count. Optional `report_path` writes a new full
JSON audit. `walk_and_store(..., report=...)` captures discovered path outcomes,
duplicate signatures, directory counts and scan/read errors while preserving
its integer return value. The walker and record builder expose optional
`on_error` callbacks; existing callers retain their default behavior.
Limited discovery remains concurrent; successful paths are processed in sorted
order to avoid arbitrary duplicate-path changes within an unchanged full scan.
The catalogue layer merges by content hash before the generic store's replace
operation, preserving absent metadata/descriptions without carrying captions
across changed content. The [main development guide](../dev.readme.md#sqlite-catalogue-schema)
contains the actual single-table data model.

`migrate_catalogue` runs explicit transactional DDL before canonical writes.
Only the allowlisted retired legacy fields are dropped; unknown columns fail.
It consolidates old timestamps and validates existing tags before committing.
`open_catalogue` applies this migration without changing generic `SQLiteStore`
behavior. Read-only legacy imports discard retired fields without modifying the
source databases. Search never performs a migration.
`build_video(..., store=...)` merges stored metadata before choosing the
filesystem-created fallback, so missing probe data cannot overwrite recording
time. A newly probed recording time can replace an older fallback. User tags
merge without being erased by an empty newly extracted list.

```powershell
python -m pytest src\tools\tests -q
```

Units use synthetic metadata, fake probes/geocoders and temporary SQLite files.
Index tests cover duplicate-path retention in reports, stable representative
paths, scan/read failures, invalid inputs, old catalogue counts and report
overwrite protection. CLI/MCP tests exercise report export through both native
interfaces without real ffprobe or model calls.
Migration tests cover physical column removal, timestamps, tags, source
preservation, idempotency and rollback after DDL/data updates.
Real reverse-geocoder/country-dataset checks moved to
`src\integration_tests\test_geocoding.py` so they are excluded before collection.

## Explicit diagnostics

`scripts\benchmark_hash.py ROOT [LIMIT]` measures partial-hash behavior.
`scripts\explore_metadata.py ROOT [LIMIT]` scans real metadata using ffprobe.
Both require an explicit root, write unique JSON reports under
`data\diagnostics`, and are opt-in real-file work, not application unit tests.
The metadata script may initialize its existing FFmpeg dependency at execution;
do not run it merely to validate imports or documentation.
