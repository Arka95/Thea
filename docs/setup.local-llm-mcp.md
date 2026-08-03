# Optional: VS Code, Qwen 3, and Thea MCP

This optional guide configures VS Code with Ollama/Qwen 3 and enables Thea's
project-scoped MCP servers. It does not cover Python project compilation or the
CUDA toolchain.

Complete [`setup.md`](setup.md) first.

## Install VS Code and Node.js

```powershell
winget install --id Microsoft.VisualStudioCode --exact
winget install --id OpenJS.NodeJS.LTS --exact
```

Open a new terminal:

```powershell
code --version
node --version
npm --version
```

Use Node.js 20 or newer.

## Install Ollama and Qwen 3

```powershell
irm https://ollama.com/install.ps1 | iex
ollama pull qwen3:8b
ollama run qwen3:8b "Reply with: Qwen 3 is ready"
```

Qwen 3 8B is appropriate for a 12 GB GPU. Use a larger Qwen 3 model only when
enough VRAM and system RAM are available.

Verify GPU use:

```powershell
ollama ps
nvidia-smi
```

## Install and configure the VS Code client

Install Cline:

```powershell
code --install-extension saoudrizwan.claude-dev
code C:\projects\Thea
```

In Cline settings:

1. Select `Ollama` as the API provider.
2. Set the base URL to `http://localhost:11434`.
3. Select `qwen3:8b`.

If necessary, start Ollama:

```powershell
ollama serve
```

## Thea's MCP configuration

The project-scoped client configuration is checked in at:

```text
.vscode/mcp.json
```

| Server | Purpose |
|--------|---------|
| `filesystem` | Read and search files inside the Thea workspace |
| `memory` | Persist project facts and relationships |
| `seq-thinking` | Structured multi-step reasoning |
| `git` | Inspect repository history and changes |

The Node servers run through `npx`; they do not require global npm installs.
Install the Git MCP executable into Thea's existing `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

## Enable and verify MCP

1. Open `C:\projects\Thea` as the VS Code workspace.
2. Open Cline's MCP/server panel.
3. Enable the servers declared in `.vscode/mcp.json`.
4. Approve filesystem access only for `C:\projects\Thea`.

Use these read-only verification prompts:

| Server | Prompt |
|--------|--------|
| `filesystem` | `List the preset files under config/presets.` |
| `memory` | `Remember that Thea supports CUDA and CPU OpenCV modes.` |
| `seq-thinking` | `Break down how a video moves through Thea.` |
| `git` | `Show the latest commit that changed requirements.txt.` |

## Usage rules

- Keep filesystem access restricted to the Thea workspace.
- Do not store credentials, video contents, or sensitive data in MCP memory.
- Keep Python MCP packages inside `.venv`.
- Use Git MCP for inspection and the terminal for explicit commits.
- Prefer the checked-in workflows under `.vscode/skills/`.

## Troubleshooting

| Problem | Resolution |
|---------|------------|
| Ollama is unavailable | Confirm `curl http://localhost:11434/api/tags` returns JSON. |
| Qwen 3 is missing | Run `ollama list` and pull `qwen3:8b` again. |
| A Node MCP server fails | Run its `npx -y <package-name> --help` command and inspect the error. |
| Git MCP is missing | Confirm `.venv\Scripts\mcp-server-git.exe` exists. |
| MCP changes are ignored | Reload the VS Code window and restart Cline. |
