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
| `walkdir.py` | Directory discovery, metadata population, storage and indexing CLI |

`thea-index` and `python -m tools.walkdir` call the same `main(argv)` function.
The default in-memory store remains ephemeral; pass `--db` for persistence.
No Thea MCP server or model runtime is created by importing these packages.

```powershell
python -m pytest src\tools\tests -q
```

Units use synthetic metadata, fake probes/geocoders and temporary SQLite files.
Real reverse-geocoder/country-dataset checks moved to
`src\integration_tests\test_geocoding.py` so they are excluded before collection.

## Explicit diagnostics

`scripts\benchmark_hash.py ROOT [LIMIT]` measures partial-hash behavior.
`scripts\explore_metadata.py ROOT [LIMIT]` scans real metadata using ffprobe.
Both require an explicit root, write unique JSON reports under
`data\diagnostics`, and are opt-in real-file work, not application unit tests.
The metadata script may initialize its existing FFmpeg dependency at execution;
do not run it merely to validate imports or documentation.
