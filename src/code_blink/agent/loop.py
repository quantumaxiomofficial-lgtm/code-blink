from __future__ import annotations
import json
import re
from typing import Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from code_blink.provider.base import LLMProvider, Message, StreamChunk
from code_blink.provider.base import Tool as ProviderTool
from code_blink.tools.registry import ToolRegistry

SYSTEM_PROMPT = (
    "You are Code Blink, an autonomous AI coding assistant running on "
    "Windows 11 Pro. Created by Big Pickle AI Model and Sato Imasu "
    "(also known as AfterBlink).\n\n"
    "## Mandatory tool usage\n"
    "You MUST use your tools. Do NOT assume or guess anything. Call the "
    "right tool first, then use its results immediately. Do not describe "
    "what a tool returned - the user can already see it in the UI.\n"
    "Just state your conclusion or next action based on the tool output.\n\n"
    "Tool reference:\n"
    "- `ls` - list directory contents\n"
    "- `tree` - show directory tree structure\n"
    "- `glob` - find files by name pattern\n"
    "- `grep` - search file contents (use include=*.py to narrow)\n"
    "- `read` - view a file\n"
    "- `edit` - replace text in an existing file\n"
    "- `write` - create/overwrite a file\n"
    "- `web_search` - search the web\n"
    "- `web_fetch` - fetch a URL\n\n"
    "## Platform\n"
    "- Windows 11 Pro. \\\\ or / both work. Drive letters exist.\n"
    "- Working directory = where the user launched code-blink from.\n"
    "- Username: quant. Use C:\\Users\\quant\\ for home.\n"
    "- Downloads=C:\\Users\\quant\\Downloads, "
    "Documents=C:\\Users\\quant\\Documents, "
    "Desktop=C:\\Users\\quant\\Desktop, "
    "Pictures=C:\\Users\\quant\\Pictures\n\n"
    "## Output rules\n"
    "- Be concise. No fluff.\n"
    "- <thinking>...</thinking> for reasoning. Final answer after </thinking>.\n"
    "- Use <status>short action phrase</status> to show what you're doing "
    "(e.g. <status>Scanning directory...</status>, "
    "<status>Reading file...</status>, "
    "<status>Writing changes...</status>). "
    "Keep it under 5 words.\n"
    "- Markdown code blocks for code.\n"
    "- When writing/editing files, summarize what changed briefly.\n"
    "- Keep calling tools and making progress until the task is done."
)


@dataclass
class LoopCallbacks:
    on_token: Callable[[str], None] | None = None
    on_thinking: Callable[[str], None] | None = None
    on_status: Callable[[str], None] | None = None
    on_tool_call: Callable[[str, dict, str], None] | None = None
    on_diff: Callable[[str, str, str], None] | None = None
    on_iteration: Callable[[int], None] | None = None
    on_done: Callable[[str], None] | None = None


CONTINUE_PROMPT = (
    "Continue working on the task. Make progress towards completing it."
)

class AgentLoop:
    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        permission_level: str = "write",
        max_iterations: int = 10,
        system_prompt: str | None = None,
        verbose_thinking: bool = True,
        autonomous: bool = False,
    ):
        self.provider = provider
        self.tools = tool_registry
        self.permission_level = permission_level
        self.max_iterations = 100 if autonomous else max_iterations
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.verbose_thinking = verbose_thinking
        self.autonomous = autonomous

    def _build_provider_tools(self) -> list[ProviderTool] | None:
        all_tools = self.tools.list()
        if not all_tools:
            return None
        return [
            ProviderTool(
                name=t.name,
                description=t.description,
                parameters={
                    "type": "object",
                    "properties": t.parameters,
                    "required": t.required,
                },
            )
            for t in all_tools
        ]

    def _strip_thinking(self, text: str) -> tuple[str, str]:
        parts = re.split(r"<thinking>(.*?)</thinking>", text, flags=re.DOTALL)
        clean = ""
        thoughts = ""
        for i, part in enumerate(parts):
            if i % 2 == 0:
                clean += part
            else:
                thoughts += part.strip() + "\n"
        clean = self._strip_answer_tags(clean).strip()
        thoughts = thoughts.strip()

        # If everything ended up inside thinking tags, split off the last line as answer
        if not clean and thoughts:
            lines = thoughts.split("\n")
            # Try to split: last paragraph is answer, rest is thinking
            answer = ""
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if line and not answer:
                    answer = line
                elif answer:
                    break
            if answer:
                # Last non-empty line is the answer
                thinking_lines = [l for l in lines if l.strip() and l.strip() != answer]
                thoughts = "\n".join(thinking_lines)
                clean = answer

        return clean, thoughts

    _WRAP_RE = re.compile(r"</?[a-zA-Z][\w ._-]*>")
    _STRIP_STATUS_RE = re.compile(r"<status>.*?</status>", re.DOTALL)

    def _strip_answer_tags(self, text: str) -> str:
        return self._WRAP_RE.sub("", text)

    async def _capture_file(self, path: str) -> str:
        p = Path(path)
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return ""
        return ""

    async def run(
        self,
        task: str,
        history: list[dict] | None = None,
        callbacks: LoopCallbacks | None = None,
    ) -> str:
        messages: list[Message] = [
            Message(role="system", content=self.system_prompt),
        ]
        if history:
            for msg in history:
                if msg["role"] in ("user", "assistant"):
                    messages.append(Message(role=msg["role"], content=msg.get("content") or ""))

        messages.append(Message(role="user", content=task))

        no_tool_count = 0
        last_output = ""

        for iteration in range(self.max_iterations):
            if callbacks and callbacks.on_iteration:
                callbacks.on_iteration(iteration + 1)

            full_content = ""
            tool_calls_pending: list[dict] | None = None
            provider_tools = self._build_provider_tools()
            tag_buf = ""
            in_thinking = False
            in_status = False

            async for chunk in self.provider.chat_stream(messages, tools=provider_tools):
                if chunk.content:
                    text = chunk.content
                    full_content += text
                    tag_buf += text

                    while tag_buf:
                        if in_thinking:
                            ci = tag_buf.find("</thinking>")
                            if ci >= 0:
                                think = tag_buf[:ci]
                                if think and callbacks and callbacks.on_thinking and self.verbose_thinking:
                                    callbacks.on_thinking(self._strip_answer_tags(think))
                                tag_buf = tag_buf[ci + len("</thinking>"):]
                                in_thinking = False
                            else:
                                if len(tag_buf) > 11:
                                    emit = tag_buf[:-11]
                                    if emit and callbacks and callbacks.on_thinking and self.verbose_thinking:
                                        callbacks.on_thinking(self._strip_answer_tags(emit))
                                    tag_buf = tag_buf[-11:]
                                else:
                                    break
                        elif in_status:
                            ci = tag_buf.find("</status>")
                            if ci >= 0:
                                status_text = tag_buf[:ci]
                                if status_text and callbacks and callbacks.on_status:
                                    callbacks.on_status(status_text)
                                tag_buf = tag_buf[ci + len("</status>"):]
                                in_status = False
                            else:
                                break
                        else:
                            ti = tag_buf.find("<thinking>")
                            if ti >= 0:
                                before = tag_buf[:ti]
                                if before and callbacks and callbacks.on_token:
                                    callbacks.on_token(self._strip_answer_tags(before))
                                tag_buf = tag_buf[ti + len("<thinking>"):]
                                in_thinking = True
                                continue
                            si = tag_buf.find("<status>")
                            if si >= 0:
                                before = tag_buf[:si]
                                if before and callbacks and callbacks.on_token:
                                    callbacks.on_token(self._strip_answer_tags(before))
                                tag_buf = tag_buf[si + len("<status>"):]
                                ci = tag_buf.find("</status>")
                                if ci >= 0:
                                    status_text = tag_buf[:ci]
                                    if status_text and callbacks and callbacks.on_status:
                                        callbacks.on_status(status_text)
                                    tag_buf = tag_buf[ci + len("</status>"):]
                                else:
                                    in_status = True
                                    break
                                continue
                            lt = tag_buf.find("<")
                            if lt >= 0:
                                rt = tag_buf.find(">", lt)
                                if rt >= 0:
                                    before = tag_buf[:lt]
                                    if before and callbacks and callbacks.on_token:
                                        callbacks.on_token(self._strip_answer_tags(before))
                                    tag_buf = tag_buf[rt + 1:]
                                else:
                                    before = tag_buf[:lt]
                                    if before and callbacks and callbacks.on_token:
                                        callbacks.on_token(self._strip_answer_tags(before))
                                    tag_buf = tag_buf[lt:]
                                    break
                            else:
                                if callbacks and callbacks.on_token:
                                    callbacks.on_token(self._strip_answer_tags(tag_buf))
                                tag_buf = ""

                if chunk.tool_calls:
                    tool_calls_pending = chunk.tool_calls

                if chunk.done:
                    break

            if tag_buf and callbacks:
                if in_thinking:
                    if callbacks.on_thinking:
                        callbacks.on_thinking(self._strip_answer_tags(tag_buf))
                else:
                    cleaned = self._strip_answer_tags(tag_buf)
                    if cleaned and callbacks.on_token:
                        callbacks.on_token(cleaned)

            if tool_calls_pending:
                messages.append(
                    Message(
                        role="assistant",
                        content=full_content,
                        tool_calls=tool_calls_pending,
                    )
                )

                for tc in tool_calls_pending:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args = {}

                    old = ""
                    path = args.get("path", "")
                    if name in ("edit", "write") and path:
                        old = await self._capture_file(path)

                    result = await self.tools.execute(name, args, self.permission_level)

                    if name in ("edit", "write") and path:
                        new = await self._capture_file(path)
                        if old != new:
                            if callbacks and callbacks.on_diff:
                                callbacks.on_diff(path, old, new)

                    messages.append(
                        Message(
                            role="tool",
                            content=result[:2000],
                            tool_call_id=tc.get("id", ""),
                        )
                    )

                    if callbacks and callbacks.on_tool_call:
                        callbacks.on_tool_call(name, args, result)

                no_tool_count = 0
                continue

            else:
                clean_final, think_final = self._strip_thinking(full_content)
                clean_final = self._STRIP_STATUS_RE.sub("", clean_final)
                clean_final = self._strip_answer_tags(clean_final).strip()
                no_tool_count += 1

                if self.autonomous:
                    # Stuck detection: same output as last time
                    if clean_final == last_output:
                        if callbacks and callbacks.on_done:
                            callbacks.on_done(clean_final)
                        return clean_final
                    last_output = clean_final

                    # Idle detection: 2 consecutive no-tool iterations
                    if no_tool_count >= 2:
                        if callbacks and callbacks.on_done:
                            callbacks.on_done(clean_final)
                        return clean_final

                    # Push continuation and keep going
                    messages.append(
                        Message(role="user", content=CONTINUE_PROMPT)
                    )
                    if callbacks and callbacks.on_token:
                        callbacks.on_token(f"\n[auto]\n")
                    continue

                if callbacks and callbacks.on_done:
                    callbacks.on_done(clean_final)
                return clean_final

        msg = f"Reached max iterations ({self.max_iterations}) without final answer."
        if callbacks and callbacks.on_done:
            callbacks.on_done(msg)
        return msg
