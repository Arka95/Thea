# CLI and MCP development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\main.py` owns argument parsing and `run_command`, the shared dispatcher.
`src\cli\commands.py` adapts crop/pan, caption and indexing APIs; existing
processing handlers now also return structured results without removing CLI
logging. `tools.walkdir.index_videos` provides the quiet indexing API used by both
interfaces; `thea-index` retains its existing console summary.

`src\cli\mcp.py` lazily imports the optional MCP v2 SDK, registers typed tools,
and calls the same dispatcher. Root `mcp_server.py` and installed `thea-mcp`
launch it. The CLI does not require the MCP extra. SDK input schemas validate
tool arguments; media bounds/codec checks remain in their owning APIs.
Each operation holds a process-local lock and resets its metrics. Only the
stdio launcher configures stderr logging; it never invokes CLI printing.

Caption defaults create a unique JPEG below the resolved `data_dir\captions`.
Explicit existing JPEG destinations are rejected. The adapter validates paths
and positive sampling/timeout settings before invoking the sampler or endpoint.
API keys are read at the interface boundary from the named environment variable
and are not included in results.

`pipeline --output` now selects the run's output root; it was previously parsed
but ignored. Other existing defaults, aliases and Python APIs are retained.

## Validation

```powershell
python -m pytest src\cli\tests src\tools\tests\test_walkdir.py src\cropandpan\tests src\sampled_captioner\tests -q
python -m black --check src\main.py src\cli src\tools\walkdir.py mcp_server.py
python -m ruff check src\main.py src\cli src\tools\walkdir.py mcp_server.py
```

Unit tests fake media APIs and endpoints. MCP tests use the SDK's in-process
client, compare tool schemas with every CLI parser, and check dispatch, defaults,
structured results and errors. They require the optional MCP v2 SDK; without it
only that protocol-test module is skipped. Subprocess/real-media protocol checks
are explicit opt-in integrations, not routine units.

Keep the root command reference, MCP parameter table, client configuration and
`.github\skills\thea-mcp\SKILL.md` consistent when changing the public interface.
The upstream [SDK documentation](https://py.sdk.modelcontextprotocol.io/) covers
the MCP v2 server/client contract.
