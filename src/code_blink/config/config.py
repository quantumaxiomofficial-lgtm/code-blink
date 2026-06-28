import sys
from pathlib import Path

from code_blink.config.schema import AppConfig
from code_blink.config.defaults import CONFIG_FILE, CONFIG_DIR, DATA_DIR, SESSIONS_DIR

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or CONFIG_FILE
    if not config_path.exists():
        return AppConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return AppConfig(**data)


def ensure_dirs():
    for d in [CONFIG_DIR, DATA_DIR, SESSIONS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def write_default_config(path: Path | None = None):
    config_path = path or CONFIG_FILE
    ensure_dirs()

    content = """[provider]
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
# workspace_path = "/path/to/workspace"

[agent]
max_retries = 3
max_context_percent = 70
auto_continue = false
verbose_thinking = true
"""

    with open(config_path, "w") as f:
        f.write(content)
