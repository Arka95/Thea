This tool helps extract stock-footage grade cinematics from videos by:

What is a good stock video window slice:

a minimum of 5 seconds footage without any unusual stutters, irregular camera movement, disruptive or inconsistent panning.


1. extracting a time based start and end window  of stable shots based on optical flow. There can be multiple such windows
2. each extracted window-slice of video is then trimmed and stored as a separate video with the name {original_video_name}_{slice_number}.{extension} . The sliced video should have the same encoding/quality as the original
3. all sliced videos would be in a folder {original_video_name}_sliced in the root directory


# Setup Intell-j + your Local LLM (optional):
Install [intellij idea](https://www.jetbrains.com/idea/) 2026 edition
## Integrate a local LLM with it to serve as mcp
Download and install [ollama](https://ollama.com/)
`irm https://ollama.com/install.ps1 | iex`

### [optional] Download and install Node.js using choco / msi:
```
powershell -c "irm https://community.chocolatey.org/install.ps1|iex"
choco install nodejs --version="24.16.0"
node -v # Should print "v24.16.0".
```

Or avoid all above and just install using the msi file: https://nodejs.org/en/download

### OLLAMA/Openclaw

Models are defualted to download in these locations:

- `Windows`: C:\Users\%username%\.ollama\models
- `macOS`: ~/.ollama/models
- `Linux`: /usr/share/ollama/.ollama/models

Run a local model like QWEN2.5 (good for under 12GB VRAM GPUs)
```
ollama launch openclaw
ollama run qwen2.5-coder:7b
```
To Run Local LLM as agent in IntelliJ, follow :
- Enable chat mode[this](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html#use-custom-models-in-ai-features):
- install from https://opencode.ai/download `npm i -g opencode-ai`
- btw open code is really great to separately have a one-stop solution to an agentic UI to do stuff.
if you want agent mode you have to add a config to %USERPROFILE%\.jetbrains\acp.json

```
{
  "default_mcp_settings": {
    "use_custom_mcp": true,
    "use_idea_mcp": true,
    "idea_mcp_allowed_tools": ["*"]
  },
  "agent_servers": {
    "Local Llama Agent": {
      "command": "qwen-agent",
      "args": ["--acp", "--model", "llama3", "--endpoint", "http://localhost:11434/v1"],
      "env": {
        "OPENAI_API_KEY": "ollama"
      }
    },
    "Local Qwen 2.5 Agent": {
      "command": "qwen-agent",
      "args": ["--acp", "--model", "qwen2.5-coder", "--endpoint", "http://localhost:11434/v1"],
      "env": {
        "OPENAI_API_KEY": "ollama"
      }
    }
  }
}
```
