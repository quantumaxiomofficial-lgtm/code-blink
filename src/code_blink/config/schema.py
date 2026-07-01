from pydantic import BaseModel, Field
from typing import Optional


class ProviderConfig(BaseModel):
    name: str = "ollama"
    url: str = "http://localhost:11434"
    model: str = "huihui_ai/lfm2.5-abliterated:1.2b-thinking"
    api_key: str | None = None
    timeout: int = 120
    max_tokens: int = 4096


class ToolConfig(BaseModel):
    permission_level: str = "write"
    web_search: bool = True
    shell_exec: bool = True


class SandboxConfig(BaseModel):
    enabled: bool = True
    temp_workspace: bool = False
    workspace_path: Optional[str] = None


class AgentConfig(BaseModel):
    max_retries: int = 3
    max_context_percent: int = 70
    auto_continue: bool = False
    verbose_thinking: bool = True
    autonomous: bool = False


class AppConfig(BaseModel):
    provider: ProviderConfig = ProviderConfig()
    tools: ToolConfig = ToolConfig()
    sandbox: SandboxConfig = SandboxConfig()
    agent: AgentConfig = AgentConfig()
