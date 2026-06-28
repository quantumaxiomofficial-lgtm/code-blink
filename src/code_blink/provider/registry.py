from code_blink.provider.base import LLMProvider, ProviderConfig
from code_blink.provider.ollama import OllamaProvider
from code_blink.provider.lmstudio import LMStudioProvider


def get_provider(
    provider_name: str,
    url: str,
    model: str,
    timeout: int = 120,
    max_tokens: int = 4096,
) -> LLMProvider:
    config = ProviderConfig(url=url, model=model, timeout=timeout, max_tokens=max_tokens)

    if provider_name == "ollama":
        return OllamaProvider(config)
    elif provider_name == "lmstudio":
        return LMStudioProvider(config)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
