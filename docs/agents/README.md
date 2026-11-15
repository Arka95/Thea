# Agent tooling

[Back to Thea](../../README.md) | [Developer guide](../dev.readme.md)

## Instructions and precedence

The parent `projectWorkspace` policy supplies shared development standards.
[AGENTS.md](../../AGENTS.md) adds Thea-specific layout and environment details.
Root `.instructions.md`, `.clinerules`, and `.github\copilot-instructions.md`
all direct their clients to that same contract.

The previous local instructions duplicated shared policy and included invented
configuration fields/APIs, automatic installs, mandatory full-suite/GPU checks,
and unrestricted memory-MCP usage. Those conflicting directions were removed.
Do not reintroduce a competing set of defaults in a client-specific file.

## Resources

| Location | Responsibility |
|----------|----------------|
| `.github\skills` | Configuration, dependencies, docs, profiling, and pipeline design workflows |
| `.github\prompts` | Reusable review, commit, debugging, test, research, and code-mapping prompts |
| `.vscode\tasks.json` | Unit tests, explicit integration tests, lint, formatting, types, and CLI tasks |
| `.vscode\launch.json` | Module-based debugging and separate opt-in integration debugging |
| `.vscode\settings.json` | Source path and unit-test discovery configuration |
| `.vscode\mcp.json` | Thea stdio server connection plus existing external clients |
| `mcp_server.py`, `src\cli\mcp.py` | Root launcher and typed Thea tools; [usage](../mcp/README.md) |
| `.github\skills\thea-mcp\SKILL.md` | CLI/MCP invocation guidance and examples |

Use built-in tools for routine work. Client discovery support is client-specific;
point a client at the checked-in resources if it does not discover them itself.
No resource here authorizes installing a server, starting a daemon, probing a GPU,
loading a model, or publishing private repository content.

The [optional local AI setup](../setup.local-llm-mcp.md) retains the existing
LM Studio/Ollama and external MCP setup instructions. It is not required for
Thea's processing APIs or unit tests.
