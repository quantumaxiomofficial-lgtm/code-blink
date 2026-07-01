from code_blink.provider.base import LLMProvider, ProviderConfig
from code_blink.provider.ollama import OllamaProvider
from code_blink.provider.lmstudio import LMStudioProvider
from code_blink.provider.openrouter import OpenRouterProvider


def get_provider(
    provider_name: str,
    url: str,
    model: str,
    api_key: str | None = None,
    timeout: int = 120,
    max_tokens: int = 4096,
) -> LLMProvider:
    config = ProviderConfig(
        url=url, model=model, api_key=api_key,
        timeout=timeout, max_tokens=max_tokens,
    )

    if provider_name == "ollama":
        return OllamaProvider(config)
    elif provider_name == "lmstudio":
        return LMStudioProvider(config)
    elif provider_name == "openrouter":
        return OpenRouterProvider(config)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
