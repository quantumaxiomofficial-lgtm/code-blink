import argparse
import sys

from code_blink.config.config import load_config, ensure_dirs, write_default_config
from code_blink.config.defaults import CONFIG_FILE


def cli():
    parser = argparse.ArgumentParser(
        prog="code-blink",
        description="A local-first AI coding agent — Ollama & LMStudio",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config file",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Write a default config file and exit",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name to use (overrides config)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["ollama", "lmstudio"],
        default=None,
        help="Provider to use (overrides config)",
    )
    parser.add_argument(
        "--permission",
        type=str,
        choices=["read", "write", "full"],
        default=None,
        help="Override permission level",
    )

    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run a task headlessly (non-interactive)")
    run_parser.add_argument("task", type=str, help="Task description")
    run_parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Continue until blocked",
    )

    args = parser.parse_args()

    if args.init_config:
        write_default_config()
        print(f"Config written to {CONFIG_FILE}")
        sys.exit(0)

    ensure_dirs()
    config = load_config(args.config)

    if args.model:
        config.provider.model = args.model
    if args.provider:
        url_map = {"ollama": "http://localhost:11434", "lmstudio": "http://localhost:1234/v1"}
        config.provider.url = url_map[args.provider]
    if args.permission:
        config.tools.permission_level = args.permission

    if args.command == "run":
        _run_headless(config, args.task, args.autonomous)
    else:
        _run_tui(config)


def _run_tui(config):
    from code_blink.tui.app import CodeBlinkApp
    app = CodeBlinkApp(config=config)
    app.run()


def _run_headless(config, task: str, autonomous: bool):
    import asyncio
    from code_blink.provider.registry import get_provider
    from code_blink.tools.registry import get_registry
    from code_blink.tools import register_all_tools
    from code_blink.agent.loop import AgentLoop

    register_all_tools()
    provider_name = config.provider.name or (
        "openrouter" if "openrouter" in config.provider.url
        else "ollama" if "11434" in config.provider.url
        else "lmstudio"
    )
    provider = get_provider(
        provider_name=provider_name,
        url=config.provider.url,
        model=config.provider.model,
        api_key=config.provider.api_key,
        timeout=config.provider.timeout,
        max_tokens=config.provider.max_tokens,
    )

    loop = AgentLoop(
        provider=provider,
        tool_registry=get_registry(),
        permission_level=config.tools.permission_level,
        verbose_thinking=config.agent.verbose_thinking,
        autonomous=autonomous,
    )

    print(f"[?]  {task}\n")

    async def run():
        result = await loop.run(
            task,
            callbacks=None,
        )
        return result

    final = asyncio.run(run())
    print(f"\n{'='*50}")
    print(final)


if __name__ == "__main__":
    cli()
