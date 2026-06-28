from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "code-blink"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DATA_DIR = CONFIG_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"

DEFAULT_PROVIDER = "ollama"
OLLAMA_DEFAULT_URL = "http://localhost:11434"
LMSTUDIO_DEFAULT_URL = "http://localhost:1234/v1"

DEFAULT_MODEL = "huihui_ai/lfm2.5-abliterated:1.2b-thinking"

PERMISSION_LEVELS = ["read", "write", "full"]
DEFAULT_PERMISSION = "write"

MAX_RETRIES = 3
MAX_CONTEXT_PERCENT = 70
