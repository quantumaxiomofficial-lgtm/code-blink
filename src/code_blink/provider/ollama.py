from __future__ import annotations
from typing import AsyncGenerator
import json

import httpx

from code_blink.provider.base import LLMProvider, ProviderConfig, Message, StreamChunk, Tool


class OllamaProvider(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base = config.url.rstrip("/")
        if not self._base.endswith("/v1"):
            self._base += "/v1"
        self._client = httpx.AsyncClient(timeout=config.timeout)

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        serialized = []
        for m in messages:
            entry = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = m.tool_calls
            serialized.append(entry)

        body = {
            "model": self.config.model,
            "messages": serialized,
            "stream": True,
            "max_tokens": self.config.max_tokens,
        }

        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        pending_tool_calls: dict[int, dict] = {}

        async with self._client.stream("POST", f"{self._base}/chat/completions", json=body) as resp:
            if resp.status_code != 200:
                text = await resp.aread()
                if resp.status_code == 404:
                    hint = f"Model '{self.config.model}' not found. Pull it:\n  ollama pull {self.config.model}"
                    raise RuntimeError(hint)
                raise RuntimeError(f"Ollama error ({resp.status_code}): {text.decode(errors='replace')[:500]}")
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    # flush any pending tool calls
                    if pending_tool_calls:
                        yield StreamChunk(
                            content="",
                            tool_calls=list(pending_tool_calls.values()),
                            done=True,
                        )
                    else:
                        yield StreamChunk(content="", done=True)
                    return

                data = json.loads(data_str)
                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                finish_reason = choices[0].get("finish_reason")

                delta_tool_calls = delta.get("tool_calls", None)
                if delta_tool_calls:
                    for tc in delta_tool_calls:
                        idx = tc.get("index", 0)
                        if idx not in pending_tool_calls:
                            pending_tool_calls[idx] = {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.get("function", {}).get("name", ""),
                                    "arguments": tc.get("function", {}).get("arguments", ""),
                                },
                            }
                        else:
                            existing = pending_tool_calls[idx]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                existing["function"]["name"] += fn["name"]
                            if fn.get("arguments"):
                                existing["function"]["arguments"] += fn["arguments"]

                if finish_reason == "tool_calls" and pending_tool_calls:
                    yield StreamChunk(
                        content="",
                        tool_calls=list(pending_tool_calls.values()),
                        done=True,
                    )
                    pending_tool_calls.clear()
                    return

                if content:
                    yield StreamChunk(content=content)

                if finish_reason == "stop":
                    yield StreamChunk(content="", done=True)
                    return

    async def list_models(self) -> list[str]:
        resp = await self._client.get(f"{self._base}/models")
        resp.raise_for_status()
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]

    async def check_health(self) -> bool:
        try:
            await self.list_models()
            return True
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()
