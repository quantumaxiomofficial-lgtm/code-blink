# Code Blink

**A local-first, open-source AI coding agent** — runs entirely on your machine via Ollama or LMStudio.

## Features

- **Purple/black Gemini-themed TUI** built with Textual/Rich
- **Agentic loop** — the AI can read, write, edit, glob, grep, list files, **run shell commands**, and search the web autonomously
- **Live streaming UI** — real-time token display, `<thinking>` blocks (grey italic), diff views (red/green), and tool call results
- **Multi-provider** — Ollama (default), LMStudio, and **OpenRouter** (cloud) via OpenAI-compatible API
- **Configurable** via `~/.config/code-blink/config.toml`
- **Headless mode** — `code-blink run "task"` for non-interactive use, `--autonomous` for multi-turn completion

## Installation

```bash
git clone https://github.com/quantumaxiomofficial-lgtm/code-blink.git
cd code-blink
pip install -e .
code-blink                    # launch TUI
code-blink run "do something" --autonomous
```

Requires **Python >= 3.10**. You need a running provider — **Ollama** (default, `http://localhost:11434`), **LMStudio** (`http://localhost:1234/v1`), or **OpenRouter** (cloud, requires API key).

### Dependencies (installed automatically by `pip install -e .`)

- `textual` — TUI framework
- `httpx` — HTTP client for provider APIs
- `pydantic` — config schema
- `rich` — terminal output + Markdown rendering
- `ddgs` — DuckDuckGo search tool
- `tomli` — TOML parsing (Python < 3.11 only; stdlib `tomllib` used on 3.11+)

> **Windows note**: uses Windows PowerShell 5.1 as the shell backend. Install via `winget install Git.Git` + `winget install Python.Python.3.12` if starting fresh.

## Usage

### TUI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/model <name>` | Switch model |
| `/models` | List available models from provider |
| `/provider <ollama|lmstudio|openrouter>` | Switch provider |
| `/apikey <key>` | Set API key (for OpenRouter) |
| `/mode <normal|autonomous>` | Set agent mode |
| `/tools` | List available tools |
| `/config` | Show current config |
| `/clear` | Clear messages |
| `/quit` | Exit |

Prefix a file with `@` to include it: `@path/to/file.py`

### CLI

```
code-blink [--config PATH] [--model NAME] [--provider ollama|lmstudio] [--permission read|write|full]
code-blink run "task" [--autonomous]
code-blink --init-config       # write default config and exit
```

## Configuration

Default config location: `~/.config/code-blink/config.toml`

```toml
[provider]
name = "ollama"
url = "http://localhost:11434"
model = "gemma4:31b-cloud"
api_key = ""
timeout = 120
max_tokens = 4096

[tools]
permission_level = "write"
web_search = true
shell_exec = true

[agent]
max_retries = 3
max_context_percent = 70
autonomous = false
auto_continue = false
verbose_thinking = true

[sandbox]
enabled = true
temp_workspace = false
workspace_path = ""
```

## How It Works

1. **Agent Loop** (`agent/loop.py`) — multi-turn tool-use loop, `max_iterations` guard, `<thinking>` tag extraction
2. **Provider** (`provider/ollama.py`, `provider/lmstudio.py`, `provider/openrouter.py`) — streaming chat completion via OpenAI-compatible API, tool call serialization
3. **Tools** (`tools/`) — `read`, `write`, `edit`, `glob`, `grep`, `ls`, `tree` (`file_ops.py`), `shell` (`shell.py`, blocked from destructive commands), `web_search` / `web_fetch` (`web_search.py`)
4. **TUI** (`tui/`) — Textual app with live streaming widgets (`StreamingText`, `ThinkingBlock`, `DiffBlock`)
5. **System prompt** — instructs the model to wrap reasoning in `<thinking>...</thinking>` and put the final answer after the closing tag

## Project Structure

```
src/code_blink/
├── agent/         — AgentLoop, system prompt, tag parsing, multi-turn loop
├── config/        — TOML config loading, schema, defaults
├── provider/      — Ollama, LMStudio & OpenRouter providers, base classes, registry
├── tools/         — file_ops, shell (safe command exec), web_search, permission layer
├── tui/           — Textual app, chat screen, custom widgets (StreamingText, DiffBlock, ThinkingBlock)
├── session/       — Session store
├── sandbox/       — Sandbox environment
└── main.py        — CLI entry point (TUI or headless mode)
```

## Troubleshooting

- **"Model not found"** — run `ollama pull <model>`
- **`check_health()` succeeds but 404 on chat** — the model must be pulled even if Ollama server is running
- **Tool call errors** — ensure the model supports function calling (tested with Llama 3.x, Qwen 2.5, Gemma-4)
