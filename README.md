# Code Blink

**A local-first, open-source AI coding agent** — runs entirely on your machine via Ollama or LMStudio.

## Features

- **Purple/black Gemini-themed TUI** built with Textual/Rich
- **Agentic loop** — the AI can read, write, edit, glob, grep, and list files autonomously
- **Live streaming UI** — real-time token display, `<thinking>` blocks (grey italic), diff views (red/green), and tool call results
- **Multi-provider** — Ollama (default) and LMStudio support via OpenAI-compatible API
- **Configurable** via `~/.config/code-blink/config.toml`
- **Headless mode** — `code-blink run "task"` for non-interactive use, `--autonomous` for multi-turn completion

## Quick Start

```bash
pip install textual httpx pydantic platformdirs rich ddgs
code-blink                   # launch TUI
code-blink run "do something" --autonomous
```

Requires Python >= 3.10 and a running Ollama/LMStudio server.

## Usage

### TUI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/model llama3.2` | Switch model |
| `/provider ollama` | Switch provider |
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
url = "http://localhost:11434"
model = "huihui_ai/lfm2.5-abliterated:1.2b-thinking"
timeout = 120
max_tokens = 4096

[tools]
permission_level = "write"
web_search = true
shell_exec = true

[sandbox]
enabled = true
temp_workspace = false

[agent]
max_retries = 3
max_context_percent = 70
verbose_thinking = true
```

## How It Works

1. **Agent Loop** (`agent/loop.py`) — multi-turn tool-use loop, `max_iterations` guard, `<thinking>` tag extraction
2. **Provider** (`provider/ollama.py`, `provider/lmstudio.py`) — streaming chat completion via OpenAI-compatible API, tool call serialization
3. **Tools** (`tools/file_ops.py`) — `read`, `write`, `edit`, `glob`, `grep`, `ls`, `web_search` (via DuckDuckGo)
4. **TUI** (`tui/`) — Textual app with live streaming widgets (`StreamingText`, `ThinkingBlock`, `DiffBlock`)
5. **System prompt** — instructs the model to wrap reasoning in `<thinking>...</thinking>` and put the final answer after the closing tag

## Project Structure

```
src/code_blink/
├── agent/         — AgentLoop, system prompt, tag parsing, multi-turn loop
├── config/        — TOML config loading, schema, defaults
├── provider/      — Ollama & LMStudio providers, base classes, registry
├── tools/         — file_ops (read/write/edit/glob/grep/ls), web search, permission layer
├── tui/           — Textual app, chat screen, custom widgets (StreamingText, DiffBlock, ThinkingBlock)
├── session/       — Session store
├── sandbox/       — Sandbox environment
└── main.py        — CLI entry point (TUI or headless mode)
```

## Troubleshooting

- **"Model not found"** — run `ollama pull <model>`
- **`check_health()` succeeds but 404 on chat** — the model must be pulled even if Ollama server is running
- **Tool call errors** — ensure the model supports function calling (tested with Llama 3.x, Qwen 2.5, Gemma-4)
