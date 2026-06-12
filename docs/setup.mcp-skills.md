# MCP (Model Context Protocol) + Local LLM Agent Setup

> Turn your local Qwen 3 (via Ollama) into a skilled agent with web search, git integration, filesystem access, knowledge graphs, and structured reasoning — fully integrated with VS Code.

> **🤖 LLM Auto-Setup Note:** This document is structured so an LLM agent can read it and automatically replicate this setup on a fresh Windows machine. All paths, commands, and configs are absolute and copy-pasteable. Sections marked with 🔧 contain executable setup steps in order.

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [🔧 Step 1: Install Ollama + Qwen 3](#-step-1-install-ollama--qwen-3)
5. [🔧 Step 2: Install VS Code + Cline Extension](#-step-2-install-vs-code--cline-extension)
6. [🔧 Step 3: Configure Cline to Use Ollama](#-step-3-configure-cline-to-use-ollama)
7. [🔧 Step 4: Install MCP Servers](#-step-4-install-mcp-servers)
8. [🔧 Step 5: Configure MCP Servers in Cline](#-step-5-configure-mcp-servers-in-cline)
9. [🔧 Step 6: Enable Web Search (Brave API Key)](#-step-6-enable-web-search-brave-api-key)
10. [🔧 Step 7: Verify Everything Works](#-step-7-verify-everything-works)
11. [Installed MCP Servers Reference](#installed-mcp-servers-reference)
12. [System Prompts for Skills](#system-prompts-for-skills)
13. [General MCP Pattern (How It Works)](#general-mcp-pattern-how-it-works)
14. [Adding More MCPs Manually](#adding-more-mcps-manually)
15. [Troubleshooting](#troubleshooting)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard (created by Anthropic) that allows LLMs to interact with external tools, data sources, and services through a standardized interface. Think of it as "USB-C for AI" — a universal plug that connects your model to capabilities like:

- Reading/writing files on disk
- Searching the web in real-time
- Running git commands (commit, diff, log, branch)
- Building persistent knowledge graphs
- Executing shell commands
- Structured multi-step reasoning

**Official spec:** https://modelcontextprotocol.io/

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  VS Code                                                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Cline Extension (MCP Client)                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Ollama API (http://localhost:11434) → Qwen 3 model     │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│         │          │          │          │          │                │
│    ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌─▼──────┐       │
│    │FS MCP  │ │Git MCP │ │Search  │ │Memory  │ │SeqThink│       │
│    │Server  │ │Server  │ │MCP     │ │MCP     │ │MCP     │       │
│    └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. User types a message in Cline (VS Code)
2. Cline sends it to Ollama (Qwen 3) with available tool definitions from MCP servers
3. Qwen 3 decides which tools to call (or responds directly)
4. Cline executes tool calls via MCP servers (stdio JSON-RPC)
5. Results are fed back to the model for the next response

**Each MCP server** is a separate process spawned by Cline, communicating over stdio using JSON-RPC 2.0.

---

## Prerequisites

| Tool | Version | Purpose | Check Command |
|------|---------|---------|---------------|
| Windows 10/11 | — | OS | `winver` |
| Node.js | 20+ | Run TypeScript MCP servers | `node -v` |
| Python | 3.12+ | Run Python MCP servers | `python --version` |
| npm | 10+ | Install npm packages | `npm -v` |
| pip | 25+ | Install Python packages | `pip --version` |
| Git | 2.40+ | Version control | `git --version` |
| VS Code | latest | Editor + Cline host | `code --version` |
| Ollama | 0.30+ | Local LLM runtime | `ollama --version` |
| GPU (optional) | NVIDIA RTX | Faster inference | `nvidia-smi` |

---

## 🔧 Step 1: Install Ollama + Qwen 3

### Install Ollama (if not installed)
```powershell
# Option A: PowerShell one-liner
irm https://ollama.com/install.ps1 | iex

# Option B: Download installer from https://ollama.com/download
```

### Start Ollama and pull Qwen 3
```powershell
# Start the Ollama server (runs on http://localhost:11434)
ollama serve

# In a new terminal — pull the Qwen 3 model
ollama pull qwen3

# Verify it works
ollama run qwen3 "Hello, what can you do?"
```

### Ollama install locations (Windows)
| Component | Path |
|-----------|------|
| Ollama binary | `%LOCALAPPDATA%\Programs\Ollama\ollama.exe` |
| Models | `%USERPROFILE%\.ollama\models\` |
| Config | `%USERPROFILE%\.ollama\` |

### GPU Configuration (optional — for faster inference)
```powershell
# Use all GPU layers for maximum performance
$env:OLLAMA_GPU_LAYERS = "99"

# Check GPU is being used
ollama ps  # Should show GPU in "PROCESSOR" column

# Monitor GPU usage
nvidia-smi -l 1
```

---

## 🔧 Step 2: Install VS Code + Cline Extension

### Install VS Code (if not installed)
```powershell
winget install Microsoft.VisualStudioCode
```

### Install Cline Extension
```powershell
# From command line
code --install-extension saoudrizwan.claude-dev

# OR: In VS Code, open Extensions (Ctrl+Shift+X) → search "Cline" → Install
```

### What is Cline?
Cline is an autonomous AI coding agent that runs inside VS Code. It:
- Connects to any LLM (OpenAI, Anthropic, Ollama, etc.)
- Has built-in terminal execution (PowerShell/CMD/bash)
- Supports MCP servers for extensible tool use
- Can read/write files, run commands, and iterate on code

---

## 🔧 Step 3: Configure Cline to Use Ollama

### In VS Code:
1. Open Cline sidebar (click the Cline icon or `Ctrl+Shift+P` → "Cline: Open")
2. Click the **Settings gear** ⚙️ in the Cline panel
3. Set:
   - **API Provider:** `Ollama`
   - **Model:** `qwen3`
   - **Base URL:** `http://localhost:11434` (default, usually auto-detected)

### Alternative: Direct config edit
VS Code settings (`Ctrl+,` → search "cline"):
```json
{
  "cline.apiProvider": "ollama",
  "cline.ollamaBaseUrl": "http://localhost:11434",
  "cline.ollamaModelId": "qwen3"
}
```

### Verify connection:
- Open Cline chat panel
- Type "Hello" — if Qwen 3 responds, you're connected
- If it fails, ensure `ollama serve` is running

### Cline Built-in Capabilities (no MCP needed):
| Capability | Description |
|------------|-------------|
| **Terminal execution** | Runs PowerShell/CMD commands in VS Code terminal |
| **File read/write** | Reads and edits files in your workspace |
| **Browser** | Can open URLs and screenshot pages |
| **Code analysis** | Understands your project context |

> **Note:** Cline already gives your local LLM the ability to execute PowerShell and Windows commands natively through the VS Code integrated terminal. No separate MCP server is needed for shell execution.

---

## 🔧 Step 4: Install MCP Servers

Run these commands in PowerShell to install all MCP servers:

```powershell
# --- Node.js MCP Servers (via npm) ---

# Filesystem: read/write/search files
npm install -g @modelcontextprotocol/server-filesystem

# Memory/Knowledge Graph: persistent entity-relation store
npm install -g @modelcontextprotocol/server-memory

# Web Search: Brave Search API integration
npm install -g @brave/brave-search-mcp-server

# Sequential Thinking: structured multi-step reasoning
npm install -g @gotza02/seq-thinking

# Playwright: FREE web browsing (no API key, unlimited)
npm install -g @playwright/mcp

# --- Python MCP Servers (via pip) ---

# Git: full git repo operations
pip install mcp-server-git
```

### Verify installations:
```powershell
# Check npm MCP packages
npm list -g --depth=0 | Select-String "mcp|modelcontext|brave|seq"

# Expected output:
# +-- @brave/brave-search-mcp-server@2.0.83
# +-- @gotza02/seq-thinking@1.3.5
# +-- @modelcontextprotocol/server-filesystem@2026.1.14
# +-- @modelcontextprotocol/server-memory@2026.1.26

# Check Python MCP packages
pip list | Select-String "mcp"

# Expected output:
# mcp-server-git    2026.6.4
```

### Install locations (Windows):
| Package | Location |
|---------|----------|
| npm global modules | `%APPDATA%\npm\node_modules\` |
| npm global binaries | `%APPDATA%\npm\` |
| pip scripts | `%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.12_*\LocalCache\local-packages\Python312\Scripts\` |
| pip packages | `%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.12_*\LocalCache\local-packages\Python312\site-packages\` |

---

## 🔧 Step 5: Configure MCP Servers in Cline

### Config file location:
```
%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

### Full configuration:

Edit the file above and replace its contents with the following JSON. **Replace `<USERNAME>` with your Windows username** and adjust the Python path if needed:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": [
        "C:\\Users\\<USERNAME>\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-filesystem\\dist\\index.js",
        "C:\\Projects"
      ],
      "disabled": false
    },
    "git": {
      "command": "C:\\Users\\<USERNAME>\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\\LocalCache\\local-packages\\Python312\\Scripts\\mcp-server-git.exe",
      "args": [],
      "disabled": false
    },
    "memory": {
      "command": "node",
      "args": [
        "C:\\Users\\<USERNAME>\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-memory\\dist\\index.js"
      ],
      "disabled": false
    },
    "brave-search": {
      "command": "node",
      "args": [
        "C:\\Users\\<USERNAME>\\AppData\\Roaming\\npm\\node_modules\\@brave\\brave-search-mcp-server\\dist\\index.js"
      ],
      "env": {
        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY_HERE"
      },
      "disabled": true
    },
    "sequential-thinking": {
      "command": "node",
      "args": [
        "C:\\Users\\<USERNAME>\\AppData\\Roaming\\npm\\node_modules\\@gotza02\\seq-thinking\\dist\\index.js"
      ],
      "disabled": false
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "disabled": false
    }
  }
}
```

### Quick setup script (auto-detects paths):
```powershell
$npmModules = (npm root -g).Trim()
$username = $env:USERNAME
$gitMcp = Get-ChildItem "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.12_*\LocalCache\local-packages\Python312\Scripts\mcp-server-git.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName

Write-Host "NPM modules path: $npmModules"
Write-Host "Git MCP path: $gitMcp"
Write-Host "Username: $username"

# Use these values to fill in the JSON config above
```

### Filesystem access scope:
The `"C:\\Projects"` argument in the filesystem config defines the **security boundary** — the model can only access files within that directory tree. Adjust as needed:
```json
"args": [
  "...server-filesystem/dist/index.js",
  "C:\\Projects",
  "C:\\Users\\<USERNAME>\\Documents"
]
```
Add multiple paths as additional args to allow access to more directories.

---

## 🔧 Step 6: Enable Web Search (Brave API Key)

1. Go to https://brave.com/search/api/
2. Sign up (free tier: **2000 queries/month**, no credit card needed)
3. Copy your API key
4. Edit the MCP config file:
   ```
   %APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
   ```
5. Replace `"YOUR_BRAVE_API_KEY_HERE"` with your actual key
6. Change `"disabled": true` to `"disabled": false` for the `brave-search` entry
7. Restart VS Code / reload Cline

---

## 🔧 Step 7: Verify Everything Works

### Restart VS Code
Close and reopen VS Code (or run `Ctrl+Shift+P` → "Developer: Reload Window").

### Check MCP servers in Cline:
1. Open Cline sidebar
2. Look for the MCP status indicator (hammer icon 🔨) — click it
3. You should see all configured servers listed as "connected" (green)

### Test each capability:

| Test prompt | Expected behavior |
|-------------|-------------------|
| "List files in C:\Projects\Thea" | Uses filesystem MCP → shows directory listing |
| "Show me the git log for this repo" | Uses git MCP → shows recent commits |
| "Remember that this project uses CUDA for GPU acceleration" | Uses memory MCP → stores as entity |
| "Search the web for the latest Ollama release notes" | Uses brave-search MCP → returns web results |
| "Think step by step about how to optimize this function" | Uses sequential-thinking MCP → structured reasoning |
| "Run nvidia-smi" | Uses Cline built-in terminal → shows GPU status |

---

## Installed MCP Servers Reference

### 1. 📁 Filesystem Server

| Property | Value |
|----------|-------|
| **Package** | `@modelcontextprotocol/server-filesystem` |
| **npm** | https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem |
| **Source** | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem |
| **Language** | TypeScript/Node.js |
| **Version installed** | 2026.1.14 |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents (text or base64) |
| `write_file` | Write/overwrite a file |
| `list_directory` | List files and subdirectories |
| `create_directory` | Create new directory |
| `move_file` | Move or rename files |
| `search_files` | Regex search across file contents |
| `get_file_info` | File metadata (size, modified, permissions) |
| `list_allowed_directories` | Show accessible paths |

---

### 2. 🔀 Git Server

| Property | Value |
|----------|-------|
| **Package** | `mcp-server-git` (PyPI) |
| **PyPI** | https://pypi.org/project/mcp-server-git/ |
| **Source** | https://github.com/modelcontextprotocol/servers/tree/main/src/git |
| **Language** | Python |
| **Version installed** | 2026.6.4 |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `git_status` | Working tree status |
| `git_log` | Commit history with filters |
| `git_diff` | Diff between refs/working tree |
| `git_commit` | Create commits (with message) |
| `git_add` | Stage files |
| `git_reset` | Unstage files |
| `git_branch` | List/create/delete branches |
| `git_checkout` | Switch branches |
| `git_show` | Show commit/object details |
| `git_clone` | Clone repositories |

---

### 3. 🧠 Memory / Knowledge Graph Server

| Property | Value |
|----------|-------|
| **Package** | `@modelcontextprotocol/server-memory` |
| **npm** | https://www.npmjs.com/package/@modelcontextprotocol/server-memory |
| **Source** | https://github.com/modelcontextprotocol/servers/tree/main/src/memory |
| **Language** | TypeScript/Node.js |
| **Version installed** | 2026.1.26 |
| **Storage** | Local JSON file (persists across sessions) |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `create_entities` | Add nodes (name, type, observations) |
| `create_relations` | Connect entities (from → relation → to) |
| `add_observations` | Add facts to existing entities |
| `search_nodes` | Query graph by name/type |
| `open_nodes` | Retrieve specific entities |
| `delete_entities` | Remove nodes |
| `delete_relations` | Remove connections |
| `delete_observations` | Remove specific facts |
| `read_graph` | Dump the entire graph |

**Knowledge Graph Usage Pattern:**
```
# Building a repo knowledge graph:
1. Scan directory structure with filesystem MCP
2. Create entities for modules, classes, configs
3. Create relations: "imports", "depends_on", "tests"
4. Add observations: "handles authentication", "uses CUDA"

# Example entities:
Entity("MotionAssessment", type="module", observations=["GPU optical flow", "7 motion categories"])
Entity("Slicer", type="module", observations=["FFmpeg lossless", "OpenCV re-encode"])
Relation("Slicer" → "depends_on" → "MotionAssessment")
```

---

### 4. 🔍 Brave Search Server

| Property | Value |
|----------|-------|
| **Package** | `@brave/brave-search-mcp-server` |
| **npm** | https://www.npmjs.com/package/@brave/brave-search-mcp-server |
| **Language** | TypeScript/Node.js |
| **Version installed** | 2.0.83 |
| **API key** | Required (free tier: 2000/month) |
| **Get key** | https://brave.com/search/api/ |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `brave_web_search` | General web search with AI summaries |
| `brave_local_search` | Local business/POI search |

---

### 5. 🧩 Sequential Thinking Server

| Property | Value |
|----------|-------|
| **Package** | `@gotza02/seq-thinking` |
| **npm** | https://www.npmjs.com/package/@gotza02/seq-thinking |
| **Language** | TypeScript/Node.js |
| **Version installed** | 1.3.5 |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `sequential_thinking` | Break problems into structured reasoning steps |

Useful for: architecture decisions, debugging complex issues, planning multi-step changes.

---

### 6. 🌐 Playwright Browser Server (FREE — No API Key)

| Property | Value |
|----------|-------|
| **Package** | `@playwright/mcp` |
| **npm** | https://www.npmjs.com/package/@playwright/mcp |
| **Source** | https://github.com/microsoft/playwright-mcp |
| **Language** | TypeScript/Node.js |
| **Version installed** | 0.0.76 |
| **API key** | ❌ None needed — completely free and unlimited |
| **License** | Apache 2.0 |

**Tools provided:**
| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to any URL |
| `browser_click` | Click elements on page |
| `browser_type` | Type into input fields |
| `browser_snapshot` | Get page accessibility tree (fast text content) |
| `browser_screenshot` | Take page screenshots |
| `browser_evaluate` | Run JavaScript on the page |
| `browser_go_back` / `browser_go_forward` | Navigation history |
| `browser_wait` | Wait for page load/element |
| `browser_tab_*` | Manage multiple tabs |

**Why Playwright over Brave Search:**
- **Free** — no API key, no monthly limits, no charges
- **Full browsing** — not just search results, but actual page content
- **Interactive** — can fill forms, click buttons, navigate SPAs
- **Local** — all browsing happens on your machine via a real browser

> **Note:** Brave Search MCP is still available in config (disabled) if you want faster structured search results in the future. Playwright gives you full browser access for free.

---

## Subagents (Multi-Agent / Parallel Execution)

### Cline Built-in Subagents (Free, works with Ollama)

Cline natively supports **subagents** — parallel mini-agents that your main agent spawns for focused tasks. This is built-in and requires **no extra MCP server**.

### Enable Subagents:
1. Open Cline sidebar in VS Code → click ⚙️ **Settings**
2. Go to **Features → Agent**
3. Ensure **`use_subagents`** is toggled **ON** (it's on by default)

### What subagents can do:
| Capability | Available |
|------------|-----------|
| Read files | ✅ |
| Search code | ✅ |
| List directories | ✅ |
| Run read-only shell commands | ✅ |
| Apply custom skills | ✅ |
| Edit files | ❌ (main agent only) |
| Web access | ❌ (main agent only) |
| Spawn further subagents | ❌ |

### How to use:
```
"Use subagents to explore the motion_assessment, slicer, and downscaler modules in parallel"

"Map out the architecture of this codebase using subagents"

"Use subagents to find all usages of HardwareProfile across the repo"
```

### When Cline auto-spawns subagents:
- Researching multiple unrelated modules
- Comparing different approaches
- Gathering broad context across a large codebase
- Analyzing separate features simultaneously

### Auto-approve subagents:
If "Read project files" is enabled in Cline's Auto Approve settings, subagent launches are automatically approved (no manual clicks needed).

### Tips for effective subagent use:
- **Be specific** — "Explore tests AND check config loader" → spawns 2 focused subagents
- **State the goal** — "Use subagents to find all error handling patterns" is better than just "use subagents"
- **Large codebases benefit most** — subagents shine when there's lots to explore in parallel

---

## System Prompts for Skills

Add these as **custom instructions** in Cline settings (`Cline Settings → Custom Instructions`) to shape the model's behavior:

### Recommended System Prompt (All-in-one)

```
You are an expert software engineer and system administrator. Follow these rules:

## Coding Standards
- SOLID principles, DRY, Clean Code
- Meaningful variable/function names, small single-responsibility functions
- Always handle errors explicitly; never swallow exceptions
- Use type hints (Python) and strict TypeScript mode
- Follow PEP 8 (Python), ESLint+Prettier (JS/TS)
- Security: validate inputs, sanitize outputs, never hardcode secrets
- Write tests for critical paths; prefer composition over inheritance

## GPU & System Knowledge
- NVIDIA GPU: nvidia-smi, CUDA toolkit, cuDNN, memory management, compute capabilities
- Windows PowerShell: cmdlets, pipelines, modules, aliases, script blocks
- Model optimization: quantization (GGUF, GPTQ, AWQ), KV-cache, batch inference, mixed precision
- Performance: profiling, bottleneck identification, hardware-aware optimization

## Tool Usage Behavior
- Use brave_web_search when: user asks about current events, latest versions, "what is the latest...", news, real-time data, or anything that may have changed since training
- Use git tools to: commit with meaningful messages, check status before operations, create feature branches
- Use memory tools to: build and maintain knowledge graphs of codebases, remember project architecture
- Use sequential_thinking for: complex multi-step problems, architecture decisions, debugging
- Use filesystem tools for: exploring unfamiliar codebases, bulk file operations

## Communication
- Be concise and direct
- Show code with context (file path + relevant surrounding lines)
- Explain "why" not just "what" for non-obvious decisions
```

---

## General MCP Pattern (How It Works)

### Protocol Basics

```
┌─────────┐     stdio (JSON-RPC 2.0)     ┌───────────┐
│  Client  │ ◄──────────────────────────► │ MCP Server │
│ (Cline)  │                              │ (process)  │
└─────────┘                              └───────────┘
```

1. **Client** spawns the MCP server as a **child process**
2. Communication happens over **stdin/stdout** using JSON-RPC 2.0
3. On startup, server declares its **capabilities** (tools, resources, prompts)
4. Client presents available tools to the LLM as part of the conversation
5. LLM decides which tool(s) to call based on user's request
6. Client executes the tool call → forwards to server → returns result to LLM

### Config Pattern (universal for any MCP client)

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "<executable>",
      "args": ["<script-path>", "<arg1>", "<arg2>"],
      "env": { "API_KEY": "value" },
      "disabled": false
    }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `command` | Yes | Executable to run: `node`, `python`, or full path to binary |
| `args` | Yes | Arguments: typically the server's entry script + config args |
| `env` | No | Environment variables passed to the server process |
| `disabled` | No | Set `true` to temporarily disable without removing config |

### Writing a Custom MCP Server (TypeScript template)

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  { name: "my-custom-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Declare available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: "my_tool",
    description: "Does something useful",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "The input query" }
      },
      required: ["query"]
    }
  }]
}));

// Handle tool invocations
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "my_tool") {
    const { query } = request.params.arguments;
    const result = `Processed: ${query}`;
    return { content: [{ type: "text", text: result }] };
  }
  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Connect via stdio
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Writing a Custom MCP Server (Python template)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("my-custom-server")

@app.list_tools()
async def list_tools():
    return [Tool(
        name="my_tool",
        description="Does something useful",
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    )]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_tool":
        return [TextContent(type="text", text=f"Processed: {arguments['query']}")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## Adding More MCPs Manually

### Step-by-step process:

#### 1. Find an MCP server
- **Official registry:** https://registry.modelcontextprotocol.io/
- **Awesome MCP Servers:** https://github.com/punkpeye/awesome-mcp-servers
- **MCP Hub:** https://mcpservers.org/
- **Glama directory:** https://glama.ai/mcp/servers
- **npm search:** `npm search mcp <keyword>`

#### 2. Install it
```powershell
# For npm packages:
npm install -g @scope/package-name

# For Python packages:
pip install mcp-server-name
```

#### 3. Find the entry point
```powershell
# For npm packages — find the main script:
$npmRoot = (npm root -g).Trim()
Get-ChildItem "$npmRoot\@scope\package-name\dist" -Filter "index.js"

# For Python packages — find the executable:
pip show mcp-server-name | Select-String "Location"
# or
where.exe mcp-server-name
```

#### 4. Add to Cline config
Edit: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

Add a new entry under `"mcpServers"`:
```json
"my-new-server": {
  "command": "node",
  "args": ["C:\\Users\\<USERNAME>\\AppData\\Roaming\\npm\\node_modules\\@scope\\package\\dist\\index.js"],
  "env": {},
  "disabled": false
}
```

#### 5. Restart Cline
`Ctrl+Shift+P` → "Developer: Reload Window" in VS Code.

### Recommended additional MCPs:

| MCP | Package | Install | Purpose |
|-----|---------|---------|---------|
| Playwright | `@playwright/mcp` | `npm i -g @playwright/mcp` | Browser automation, web scraping |
| Docker | `mcp-docker` | `npm i -g mcp-docker` | Container management |
| PostgreSQL | `@modelcontextprotocol/server-postgres` | `npm i -g @modelcontextprotocol/server-postgres` | Database queries |
| Azure | `@azure/mcp` | `npm i -g @azure/mcp` | Azure cloud resource management |
| Fetch/HTTP | `@anthropic-ai/mcp-fetch` | `npm i -g @anthropic-ai/mcp-fetch` | HTTP requests and URL fetching |

---

## Troubleshooting

### Common Issues

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Ollama not connecting | `curl http://localhost:11434/api/tags` fails | Run `ollama serve` first |
| Cline can't find model | Settings show no models | Check Ollama base URL is `http://localhost:11434` |
| MCP server "not found" | Red indicator in Cline MCP panel | Verify absolute paths in config JSON |
| Git MCP not on PATH | `mcp-server-git` command not found | Use full path in config (see Step 5) |
| Brave search 401 error | Invalid API key | Check key at https://brave.com/search/api/ |
| Model not calling tools | Responds without using MCPs | Qwen 3 supports tools natively; check Cline "tool use" is enabled |
| Memory not persisting | Knowledge graph resets | Check write permissions; memory stores in working directory |
| Slow responses | Model takes >30s | Reduce model size or use GPU (`OLLAMA_GPU_LAYERS=99`) |

### Diagnostic commands
```powershell
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check GPU usage
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv

# Check all npm MCP packages
npm list -g --depth=0 | Select-String "mcp|modelcontext|brave|seq"

# Check Python MCP packages
pip list | Select-String "mcp"

# Test filesystem MCP server manually
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | node "$env:APPDATA\npm\node_modules\@modelcontextprotocol\server-memory\dist\index.js"

# Find Cline config
explorer "$env:APPDATA\Code\User\globalStorage\saoudrizwan.claude-dev\settings"
```

### Reset MCP config
If things go wrong, reset to empty config:
```powershell
Set-Content "$env:APPDATA\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json" '{"mcpServers":{}}'
```

---

## Summary of Installed Components

| Component | Type | Version | Location |
|-----------|------|---------|----------|
| Ollama | LLM Runtime | 0.30.7 | `%LOCALAPPDATA%\Programs\Ollama\` |
| Qwen 3 | Model | latest | `%USERPROFILE%\.ollama\models\` |
| Cline | VS Code Extension | latest | VS Code extensions dir |
| `@modelcontextprotocol/server-filesystem` | npm MCP | 2026.1.14 | `%APPDATA%\npm\node_modules\` |
| `@modelcontextprotocol/server-memory` | npm MCP | 2026.1.26 | `%APPDATA%\npm\node_modules\` |
| `@brave/brave-search-mcp-server` | npm MCP | 2.0.83 | `%APPDATA%\npm\node_modules\` |
| `@gotza02/seq-thinking` | npm MCP | 1.3.5 | `%APPDATA%\npm\node_modules\` |
| `@playwright/mcp` | npm MCP | 0.0.76 | `%APPDATA%\npm\node_modules\` |
| `mcp-server-git` | pip MCP | 2026.6.4 | Python312 Scripts |

---

## Quick Reference Card

```
# Start everything:
ollama serve                          # Terminal 1: start LLM server
code .                                # Open VS Code with Cline

# In Cline (VS Code):
# - MCP servers auto-start when Cline activates
# - Just start chatting with the model

# Useful Ollama commands:
ollama list                           # Show installed models
ollama ps                             # Show running models + GPU usage
ollama pull qwen3                     # Download/update model
ollama rm <model>                     # Remove a model

# GPU monitoring:
nvidia-smi                            # One-shot GPU status
nvidia-smi -l 1                       # Continuous monitoring (1s interval)
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```
