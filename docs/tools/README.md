# Video Indexing

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

Index source videos without altering them, including offline country lookup and
approximate folder-inferred locations:

```powershell
thea index "E:\2026 USA" --report-path "E:\Thea\scan_2026.json" --geocode --infer-loc
```

`thea index` and `thea-index` expose the same arguments; MCP tool `index` uses
`root`, `limit`, `report_path`, `probe`, `geocode` and `infer_loc`. See
[MCP usage](../mcp/README.md). `thea index` prints a JSON summary; the legacy
`thea-index` alias retains its human-readable console summary.

Every catalogue operation uses configured **`data_dir\video-index.sqlite3`**;
there is no per-command database override or ephemeral production catalogue.
The optional positional `LIMIT` still works. `--geocode` and
`--infer-loc` enable metadata probing automatically; `--probe` enables probing
alone. Zero-coordinate placeholders, out-of-range GPS and malformed location
tags are ignored, allowing folder inference when available. Valid embedded GPS
takes precedence over inferred locations. Records are deduplicated by content
hash, so duplicate copies retain one catalogue path.
Offline country lookup uses nearest-city data, so results near borders and
folder-inferred locations are approximate.

## Stored metadata

The [complete schema](../dev.readme.md#sqlite-catalogue-schema) keeps file identity,
device, basic dimensions/frame rate/duration, description, user-managed `tags`
and only `latitude`, `longitude`, `country`, `state`, `location` for location.
Technical video/audio/container fields, all video/audio/subtitle/data stream counts,
separate file-tag columns, raw ffprobe JSON and provenance columns are ignored,
even when present in probe output.
`tags` is a JSON-array column (strings), returned as an array; file metadata tags
do not populate it. Reindexing and captioning preserve existing tags.

Only `creation_time` is stored: embedded recording time takes precedence over
filesystem creation time. `--probe` reads embedded timestamps from format or
video-stream tags; without probing, an existing recording time is retained,
otherwise filesystem creation time is stored as UTC ISO 8601. Filesystem
modification time is never used. Embedded timezone text is preserved; filesystem
creation time may reset when a file is copied.

Writable catalogue operations automatically migrate the canonical schema in one
transaction, removing the retired columns while preserving retained values,
captions and tags. Old `created_time` supplies the fallback only where
`creation_time` is missing. Unexpected columns or a failed migration cause a
rollback instead of silently discarding unknown data. `index` returns the actual
physical columns and removed columns under `schema`, with record/caption counts
at migration time, before the scan. No backup/manifest file is created.
Search stays read-only and asks for `index`/`importindex` if migration is needed.
Existing MCP server processes must be reloaded to run updated code.

## Import, caption and search

```powershell
thea importindex "E:\Thea\old-index.sqlite3" "E:\Thea\old-trip.sqlite3"
thea caption "E:\Arunachal\drone" --model "your-vision-model"
thea search "drone footage in Arunachal for nature" --limit 10
```

`importindex` opens sources read-only, ignores explicitly retired legacy columns,
rejects genuinely unknown columns, and merges by content hash into the configured store.
Existing nonempty descriptions win conflicts; returned counts disclose them.
Different hashes claiming the same path are rejected instead of silently
deleting a record. Sources remain untouched; retain them until verification.
Import commits per record, so a failed import may have persisted earlier rows;
reruns are idempotent.

Captioning saves successful text in `videos.description`, retaining indexed
metadata. Indexed country/state enrich prompts automatically; unique
word-prefix state names such as `Arunachal` can match `Arunachal Pradesh`.
Folder-based locale is explicitly approximate, never replacement GPS.
Reindexing preserves descriptions for the same content hash; changed content
does not inherit old captions.

`search` (MCP: `search(query, limit)`) returns all retained record fields, including
array-valued tags, plus computed relevance `score` and current file-existence
`exists`. Neither computed value is stored.
It does not create symlinks. Each meaningful query term must match indexed
text; filler words are ignored. `nature` expands to landscape/forest/mountain/
river/lake/waterfall terms and `drone` to drone/aerial/overhead terms.
Description matches weigh more than tags, locale, names or paths.
This is bounded weighted substring search, not embeddings or a visual
classifier: missing descriptions do not establish nature content.
Queries allow at most eight meaningful terms, with 1-100 returned results;
all query values are bound SQL parameters.

## Count audits

The JSON response's `scan` describes only this invocation:

| Field | Meaning |
|-------|---------|
| `discovered` / `saved` / `skipped` | Video paths found, successfully stored, or unreadable during stat/hash |
| `unique_contents` / `duplicates` | Distinct partial hashes in this scan and additional paths sharing them |
| `directories` | Discovered/saved/skipped counts for each containing directory |
| `error_count` / `errors` | Scan/read errors, with up to eight path/stage/error-type samples |
| `complete` / `limited` | Whether discovery/reads had no recorded failures; whether a positive limit was requested |

The top-level `saved` remains the number of successful path-save attempts.
Top-level `distinct` counts the **entire database**, including earlier roots
and scans; it is not this invocation's discovered count.

Use `--report-path NEW.json` (MCP: `report_path`) to persist the full path
manifest and all errors, rather than only the response's eight record/error
samples. Existing reports are not overwritten. Duplicate content still has one
catalogue row, but the report retains every discovered copy's path. Processing
order is sorted so the retained duplicate path is stable for an unchanged,
unlimited scan; it is not necessarily the original copy.

Missing/non-directory roots and nonpositive limits are rejected. Directory
access failures and files disappearing or becoming unreadable during indexing
produce an incomplete scan instead of silently appearing as a smaller success.
Metadata probing can still fail while retaining filesystem-only records;
`complete` does not certify ffprobe metadata coverage.

This is a live filesystem scan, not an atomic snapshot. A limit selects paths
in concurrent discovery order, and a report cannot explain changes that
happened before its scan. Fast partial hashes are not proof of byte-for-byte
equality. Previously indexed missing/moved files are not automatically deleted.
