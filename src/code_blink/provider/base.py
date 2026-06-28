from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    required: list[str] = field(default_factory=list)


@dataclass
class Message:
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class StreamChunk:
    content: str
    tool_calls: list[dict] | None = None
    done: bool = False


@dataclass
class ProviderConfig:
    url: str
    model: str
    timeout: int = 120
    max_tokens: int = 4096


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        ...
