# Optional: VS Code, Qwen 3, and Thea MCP

This optional guide configures VS Code with Qwen 3 through LM Studio
(preferred) or Ollama, and enables Thea's project-scoped MCP servers. It does
not cover Python project compilation or the CUDA toolchain.

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

## Preferred: Install LM Studio and Qwen 3 14B

Install and open LM Studio:

```powershell
winget install --id ElementLabs.LMStudio --exact
```

In LM Studio:

1. Open **Discover** and search for `Qwen3 14B`.
2. Select the GGUF model and download the `Q4_K_M` variant (about 9 GB).
3. Open **My Models**, find Qwen 3 14B, and select its gear icon.
4. Save these per-model defaults:

| Setting | Recommended value for RTX 4070 SUPER 12 GB |
|---------|---------------------------------------------|
| GPU offload | Maximum |
| Context length | 8192 |
| Flash Attention | On |
| K cache quantization | `Q8_0` |
| V cache quantization | `Q8_0` |
| Parallel requests | 1 |

KV caching is automatically enabled when the model loads. The 8192-token
context leaves enough VRAM for the model weights, runtime, and KV cache. If
`Q8_0` cache quantization is unavailable, keep the default cache type and do
not increase the context length.

Load the model with the identifier `qwen3-14b`, then start the server from
LM Studio's **Developer** tab on port `1234`.

The equivalent CLI commands are available after LM Studio has been opened at
least once:

```powershell
$lms = "$env:LOCALAPPDATA\Programs\LM Studio\resources\app\.webpack\lms.exe"
& $lms get qwen/qwen3-14b@q4_k_m --gguf -y
& $lms load qwen/qwen3-14b --gpu max --context-length 8192 --identifier qwen3-14b
& $lms server start
```

The CLI uses the Flash Attention and KV-cache defaults saved in **My Models**.
Verify that the API and GPU offload are active:

```powershell
Invoke-RestMethod http://localhost:1234/v1/models
nvidia-smi
```

## Alternative: Install Ollama and Qwen 3

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



For the preferred LM Studio setup, configure Cline as shown:

<table>
  <tr>
    <td width="58%" valign="top">
      <ol>
      <li>Install Cline 
          <code>code --install-extension saoudrizwan.claude-dev</code>
        </li>
        <li>Select <code>LM Studio</code> as the API provider.</li>
        <li>Leave <strong>Use custom base URL</strong> disabled to use the default <a>http://localhost:1234</a>.</li>
        <li>Select <code>qwen3-14b</code>.</li>
        <li>Confirm that the detected context window is <code>8192</code>.</li>
        <li>Enable <strong>Use compact prompt</strong> for the 8K context window.</li>
      </ol>
      <p>The MCP and Focus Chain warning is a Cline LM Studio-provider limitation, not a connection error.</p>
      <p>If the dedicated LM Studio provider is unavailable, use Cline's
OpenAI-compatible provider with <a>http://localhost:1234/v1</a> as the base URL.
LM Studio does not require an API key unless authentication was explicitly
enabled.</p>
      <p>For the Ollama alternative:</p>
      <ol>
      <li>Select Ollama as the API provider.</li>
      <li>Set base url as <a>http://localhost:1234</a></li>
      <li>If necessary, Start Ollama :
      <code>ollama serve</code></li>
      </ol>
    </td>
    <td width="42%" align="right" valign="top">
      <img src="images/cline-lmstudio-qwen3-14b.png" alt="Cline configured with the LM Studio qwen3-14b model" width="340">
    </td>
  </tr>
</table>


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
| LM Studio is unavailable | Start LM Studio and confirm `Invoke-RestMethod http://localhost:1234/v1/models` returns the loaded model. |
| Qwen 3 is not listed by LM Studio | Confirm the model is loaded with the identifier `qwen3-14b`, then restart the local server. |
| Model loading exhausts VRAM | Use `Q4_K_M`, 8192 context, Q8 KV cache, one parallel request, and maximum GPU offload. |
| Ollama is unavailable | Confirm `curl http://localhost:11434/api/tags` returns JSON. |
| Qwen 3 is missing | Run `ollama list` and pull `qwen3:8b` again. |
| A Node MCP server fails | Run its `npx -y <package-name> --help` command and inspect the error. |
| Git MCP is missing | Confirm `.venv\Scripts\mcp-server-git.exe` exists. |
| MCP changes are ignored | Reload the VS Code window and restart Cline. |
