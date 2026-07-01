import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Static, Input
from textual.containers import Container

from code_blink.config.schema import AppConfig
from code_blink.tui.widgets.streaming_text import StreamingText, ThinkingBlock, _make_icon, _esc
from code_blink.tui.widgets.diff_block import DiffBlock
from code_blink.provider.registry import get_provider
from code_blink.session.store import SessionStore
from code_blink.tools.registry import get_registry
from code_blink.tools import register_all_tools
from code_blink.agent.loop import AgentLoop, LoopCallbacks
from code_blink.config.defaults import CONFIG_FILE


class BlinkHeader(Static):
    def render(self):
        ts = datetime.now().strftime("%H:%M")
        return f"[bold #c4b5fd] Code Blink [/][#2a1f45]  •  [/][#7c6fa0]{ts}[/]"


class WelcomeMessage(Static):
    def render(self):
        ts = datetime.now().strftime("%H:%M")
        return (
            "[bold #c4b5fd]Code Blink[/]\n"
            "[#e2dff0]A local-first AI coding agent[/]\n"
            f"[bold #8b5cf6][CodeBlink][/] [#7c6fa0]  {ts}[/]\n"
            "[#7c6fa0]Type a prompt.  /help for commands.  @file to include files.[/]"
        )


class ChatScreen(Screen):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.blink_config = config
        self.store = SessionStore()
        self._streaming = False
        self._provider = None
        self._loop: AgentLoop | None = None
        self._thinking_widget: ThinkingBlock | None = None
        self._agent_widget: StreamingText | None = None
        self._token_count = 0
        self._stream_start_time = 0.0
        self._phase = "ready"
        self._iter_count = 0

    def compose(self) -> ComposeResult:
        yield BlinkHeader(id="blink-header")
        with Container(id="chat-area"):
            yield WelcomeMessage(id="welcome")
            yield Container(id="message-log")
        yield Static(id="status-bar")
        yield Input(placeholder="[CodeBlink]  ask me anything...", id="prompt-input")

    def on_mount(self):
        register_all_tools()
        self.query_one("#prompt-input", Input).focus()
        self._init_provider()

    def _init_provider(self):
        cfg = self.blink_config.provider
        self._provider = get_provider(
            provider_name=cfg.name or "ollama",
            url=cfg.url,
            model=cfg.model,
            api_key=cfg.api_key,
            timeout=cfg.timeout,
            max_tokens=cfg.max_tokens,
        )
        autonomous = self.blink_config.agent.autonomous
        self._loop = AgentLoop(
            provider=self._provider,
            tool_registry=get_registry(),
            permission_level=self.blink_config.tools.permission_level,
            verbose_thinking=self.blink_config.agent.verbose_thinking,
            autonomous=autonomous,
        )
        self.store.create_session(cfg.model, cfg.url)

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return
        self.query_one("#prompt-input", Input).clear()

        if text.startswith("/"):
            self._handle_command(text)
            return

        asyncio.create_task(self._handle_prompt(text))

    def _handle_command(self, cmd: str):
        parts = cmd.split()
        command = parts[0].lower()

        if command == "/quit":
            self.store.close()
            self.app.exit()
        elif command == "/clear":
            self.clear_messages()
        elif command == "/help":
            self._add_message(
                "/help     - this help\n"
                "/models   - list available models\n"
                "/model X  - switch to model X\n"
                "/provider <ollama|lmstudio|openrouter> - switch provider\n"
                "/apikey <key> - set API key (for OpenRouter)\n"
                "/mode <normal|autonomous> - set agent mode\n"
                "/tools    - list available tools\n"
                "/config   - show config\n"
                "/clear    - clear messages\n"
                "/quit     - exit Code Blink\n\n"
                "Prefix a file with @ to include it: @path/to/file.py",
                "system",
            )
        elif command == "/models":
            asyncio.create_task(self._list_models())
        elif command == "/provider":
            if len(parts) >= 2 and parts[1] in ("ollama", "lmstudio", "openrouter"):
                self._switch_provider(parts[1])
            else:
                self._add_message("Usage: /provider <ollama|lmstudio|openrouter>", "system")
        elif command == "/model":
            if len(parts) >= 2:
                self.blink_config.provider.model = parts[1]
                self._save_config()
                self._add_message(f"Switched model to: {parts[1]}", "system")
            else:
                self._add_message(f"Current model: {self.blink_config.provider.model}", "system")
        elif command == "/tools":
            reg = get_registry()
            tools = reg.list()
            lines = [f"  {t.name} ({t.required_permission}) — {t.description[:60]}" for t in tools]
            self._add_message("Available tools:\n" + "\n".join(lines), "system")
        elif command == "/apikey":
            if len(parts) >= 2:
                self.blink_config.provider.api_key = parts[1]
                self._save_config()
                self._init_provider()
                self._add_message("API key updated and provider re-initialized.", "system")
            else:
                self._add_message("Usage: /apikey <your_key>", "system")
        elif command == "/mode":
            if len(parts) >= 2 and parts[1] in ("normal", "autonomous"):
                self.blink_config.agent.autonomous = parts[1] == "autonomous"
                self._save_config()
                self._add_message(f"Mode set to {parts[1]}. Restart for autonomous mode.", "system")
            else:
                current = "autonomous" if self.blink_config.agent.autonomous else "normal"
                self._add_message(f"Current mode: {current}\nUsage: /mode <normal|autonomous>", "system")
        elif command == "/config":
            self._add_message(
                f"Provider: {self.blink_config.provider.name or 'detect'} @ {self.blink_config.provider.url}\n"
                f"Model: {self.blink_config.provider.model}\n"
                f"API key: {'set' if self.blink_config.provider.api_key else 'not set'}\n"
                f"Mode: {'autonomous' if self.blink_config.agent.autonomous else 'normal'}\n"
                f"Permission: {self.blink_config.tools.permission_level}\n"
                f"Sandbox: {'on' if self.blink_config.sandbox.enabled else 'off'}"
                f"\nTools: {len(get_registry().list())} registered",
                "system",
            )
        else:
            self._add_message(f"Unknown command: {command}", "system")

    async def _handle_prompt(self, text: str):
        if self._streaming:
            self._add_message("Already streaming a response — wait for it to finish.", "system")
            return

        try:
            welcome = self.query_one("#welcome", WelcomeMessage)
            welcome.remove()
        except Exception:
            pass

        text, file_refs = self._resolve_file_refs(text)
        if file_refs:
            for ref, content in file_refs:
                text += f"\n\n<file path='{ref}'>\n{content}\n</file>"
            self._add_message(text, "user")
        else:
            self._add_message(text, "user")

        self._streaming = True
        self._token_count = 0
        self._stream_start_time = __import__("time").time()
        self._iter_count = 0
        input_widget = self.query_one("#prompt-input", Input)
        input_widget.disabled = True
        self._update_status("streaming", 0)

        try:
            alive = await self._provider.check_health()
            if not alive:
                self._add_message(
                    f"Can't reach {self.blink_config.provider.url}\n"
                    f"Make sure the server is running: ollama serve\n"
                    f"Or switch provider via /provider",
                    "system",
                )
                return

            log = self.query_one("#message-log", Container)
            self._agent_widget = None
            self._thinking_widget = None

            history = []
            if self.store.current_session_id:
                history = self.store.get_history(self.store.current_session_id)

            self._status_timer = self.set_interval(0.5, self._tick_status)

            callbacks = LoopCallbacks(
                on_token=lambda t: self._on_token(t, log),
                on_thinking=lambda t: self._on_thinking(t, log),
                on_status=lambda s: self._on_status(s),
                on_tool_call=lambda n, a, r: self._on_tool_result(n, a, r, log),
                on_diff=lambda p, o, n: self._on_diff(p, o, n, log),
                on_iteration=lambda i: self._on_iteration(i, log),
                on_done=lambda f: self._on_stream_done(),
            )

            final = await self._loop.run(text, history=history, callbacks=callbacks)
            self.store.save_message("user", text)
            self.store.save_message("assistant", final)

        except Exception as e:
            err = str(e)
            self._add_message(f"Error: {err}", "system")
        finally:
            self._streaming = False
            self._phase = "ready"
            self._update_status("ready")
            if hasattr(self, '_status_timer'):
                try:
                    self._status_timer.stop()
                except Exception:
                    pass
            input_widget.disabled = False
            input_widget.focus()

    def _get_or_create_agent_widget(self, log: Container) -> StreamingText:
        # If a thinking block is active but tokens are coming, close it first
        if self._thinking_widget is not None:
            self._thinking_widget = None
        if self._agent_widget is None:
            self._agent_widget = StreamingText(role="agent")
            log.mount(self._agent_widget)
            log.scroll_end()
        return self._agent_widget

    def _scroll_bottom(self, log: Container):
        try:
            if log.scroll_y >= log.max_scroll_y - 1:
                log.scroll_end(animate=False)
        except Exception:
            pass

    def _on_token(self, token: str, log: Container):
        w = self._get_or_create_agent_widget(log)
        w.append_token(token)
        self._token_count += 1
        self._update_status("streaming")
        self._scroll_bottom(log)

    def _on_thinking(self, text: str, log: Container):
        if self._thinking_widget is None:
            if self._agent_widget is not None:
                self._agent_widget.finish_stream()
                self._agent_widget = None
            self._thinking_widget = ThinkingBlock()
            log.mount(self._thinking_widget)
        self._thinking_widget.append(text)
        self._update_status("thinking")
        self._scroll_bottom(log)

    def _on_status(self, text: str):
        # Show AI-generated status text next to the agent name
        if self._agent_widget is not None:
            self._agent_widget.set_status(text)

    def _on_tool_result(self, name: str, args: dict, result: str, log: Container):
        ts = datetime.now().strftime("%H:%M")
        display = result[:2000] if len(result) > 2000 else result
        styled = f"[#8b5cf6][>] [/][#7c6fa0]tool:{name}  {ts}[/]\n[#a78bfa]{_esc(display)}[/]"
        result_widget = Static(styled)
        try:
            log.mount(result_widget)
            self._scroll_bottom(log)
        except Exception:
            pass

    def _on_diff(self, path: str, old: str, new: str, log: Container):
        try:
            block = DiffBlock(old, new, path)
            log.mount(block)
            self._scroll_bottom(log)
        except Exception:
            pass

    def _on_stream_done(self):
        if self._agent_widget:
            try:
                self._agent_widget.finish_stream()
            except Exception:
                pass
        self._agent_widget = None
        self._thinking_widget = None
        self._phase = "ready"
        self._update_status("ready")
        if hasattr(self, '_status_timer'):
            try:
                self._status_timer.stop()
            except Exception:
                pass

    def _on_iteration(self, iteration: int, log: Container):
        # Reset widget state between agent loop iterations to keep ordering clean
        self._iter_count = iteration
        if iteration > 1:
            if self._agent_widget is not None:
                try:
                    self._agent_widget.finish_stream()
                except Exception:
                    pass
                self._agent_widget = None
            self._thinking_widget = None
        self._update_status("streaming")

    def _update_status(self, phase: str, toks: int | None = None):
        self._phase = phase
        elapsed = __import__("time").time() - self._stream_start_time if self._stream_start_time else 0
        toks = self._token_count if toks is None else toks
        tps = toks / elapsed if elapsed > 0 else 0
        spinner = "[#8b5cf6]●[/]" if phase == "streaming" else "[#c4b5fd]⋯[/]" if phase == "thinking" else "[#7c6fa0]○[/]"
        phase_label = {"ready": "ready", "streaming": "streaming", "thinking": "thinking"}.get(phase, phase)
        if phase == "ready":
            text = f"[#7c6fa0]{spinner}  {phase_label}[/]"
        elif phase == "thinking":
            text = f"{spinner}  [italic #7c6fa0]{phase_label}[/]  [dim #5a4d7a]{toks}tok  {tps:.1f}t/s  {elapsed:.1f}s[/]"
        else:
            text = f"{spinner}  [#7c6fa0]{phase_label}[/]  [dim #5a4d7a]{toks}tok  {tps:.1f}t/s  {elapsed:.1f}s[/]"
        try:
            bar = self.query_one("#status-bar", Static)
            bar.update(text)
        except Exception:
            pass

    def _tick_status(self):
        if self._phase != "ready":
            self._update_status(self._phase)

    def _resolve_file_refs(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        refs = re.findall(r'@([\w./\\-]+(?:\.[\w]+)+)', text)
        if not refs:
            return text, []

        resolved = []
        for ref in refs:
            path = Path(ref)
            if path.exists() and path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    resolved.append((ref, content))
                except Exception:
                    pass

        return text, resolved

    def _add_message(self, text: str, role: str):
        log = self.query_one("#message-log", Container)
        ts = datetime.now().strftime("%H:%M")

        if role == "user":
            styled = f"{_make_icon('user')}[#7c6fa0]  {ts}[/]\n[#e2dff0]{_esc(text)}[/]"
        elif role == "system":
            styled = f"[dim #7c6fa0]  {_esc(text)}[/]"
        else:
            styled = f" {ts}]  {text}"

        msg = Static(styled)
        log.mount(msg)
        log.scroll_end()

    def clear_messages(self):
        log = self.query_one("#message-log", Container)
        log.remove_children()
        self._agent_widget = None
        self._thinking_widget = None

    def _save_config(self):
        try:
            cfg = self.blink_config
            # Read existing file to preserve unknown keys
            existing = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "rb") as f:
                    existing = tomllib.load(f)
            # Merge in-memory config into existing dict
            provider = existing.get("provider", {})
            provider["name"] = cfg.provider.name
            provider["url"] = cfg.provider.url
            provider["model"] = cfg.provider.model
            provider["api_key"] = cfg.provider.api_key or ""
            provider["timeout"] = cfg.provider.timeout
            provider["max_tokens"] = cfg.provider.max_tokens
            existing["provider"] = provider
            tools = existing.get("tools", {})
            tools["permission_level"] = cfg.tools.permission_level
            tools["web_search"] = cfg.tools.web_search
            tools["shell_exec"] = cfg.tools.shell_exec
            existing["tools"] = tools
            sandbox = existing.get("sandbox", {})
            sandbox["enabled"] = cfg.sandbox.enabled
            sandbox["temp_workspace"] = cfg.sandbox.temp_workspace
            existing["sandbox"] = sandbox
            agent = existing.get("agent", {})
            agent["max_retries"] = cfg.agent.max_retries
            agent["max_context_percent"] = cfg.agent.max_context_percent
            agent["auto_continue"] = cfg.agent.auto_continue
            agent["verbose_thinking"] = cfg.agent.verbose_thinking
            agent["autonomous"] = cfg.agent.autonomous
            existing["agent"] = agent
            # Write back as TOML
            def _val(v):
                if isinstance(v, bool):
                    return str(v).lower()
                if isinstance(v, str):
                    return f'"{v}"'
                return str(v)
            lines = []
            for section, keys in existing.items():
                lines.append(f"[{section}]")
                for k, v in keys.items():
                    lines.append(f"{k} = {_val(v)}")
                lines.append("")
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            pass

    def _switch_provider(self, name: str):
        url_map = {
            "ollama": "http://localhost:11434",
            "lmstudio": "http://localhost:1234/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        model_map = {
            "ollama": "huihui_ai/lfm2.5-abliterated:1.2b-thinking",
            "lmstudio": "local-model",
            "openrouter": "google/gemini-2.0-flash-exp:free",
        }
        self.blink_config.provider.name = name
        self.blink_config.provider.url = url_map[name]
        self.blink_config.provider.model = model_map[name]
        if name == "openrouter" and not self.blink_config.provider.api_key:
            self._add_message("No API key set for OpenRouter. Set it via config file or /apikey <key>", "system")
        self._save_config()
        self._init_provider()
        self._add_message(f"Switched to {name} at {url_map[name]}", "system")

    async def _list_models(self):
        provider = self._provider
        if not provider:
            self._add_message("No provider connected.", "system")
            return
        try:
            models = await provider.list_models()
            if models:
                self._add_message("Available models:\n" + "\n".join(f"  {m}" for m in models), "system")
            else:
                self._add_message("No models found.", "system")
        except Exception as e:
            self._add_message(f"Failed to list models: {e}", "system")

    def on_screen_resume(self):
        self.query_one("#prompt-input", Input).focus()
