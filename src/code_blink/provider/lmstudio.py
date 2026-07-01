from code_blink.provider.ollama import OllamaProvider


class LMStudioProvider(OllamaProvider):
    def __init__(self, config):
        super().__init__(config)
