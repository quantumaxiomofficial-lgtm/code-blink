from code_blink.tools.registry import ToolDef, register_tool
from code_blink.tools.file_ops import (
    tool_read,
    tool_write,
    tool_edit,
    tool_glob,
    tool_grep,
    tool_ls,
    tool_tree,
)
from code_blink.tools.shell import tool_shell
from code_blink.tools.web_search import tool_web_search, tool_web_fetch


def register_all_tools():
    register_tool(ToolDef(
        name="read",
        description="Read a file from disk. Use this when you need to see the contents of a file the user mentioned or you found with glob/ls.",
        parameters={
            "path": {"type": "string", "description": "Path to the file to read"},
            "offset": {"type": "integer", "description": "Skip this many lines from the start (0 = beginning)", "default": 0},
            "limit": {"type": "integer", "description": "Max characters to return (default: 2000)", "default": 2000},
        },
        required=["path"],
        handler=tool_read,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="write",
        description="Create a new file or overwrite an existing one with the given content. Creates folders automatically.",
        parameters={
            "path": {"type": "string", "description": "Where to write the file (path + filename)"},
            "content": {"type": "string", "description": "Full content to write into the file"},
        },
        required=["path", "content"],
        handler=tool_write,
        required_permission="write",
    ))

    register_tool(ToolDef(
        name="edit",
        description="Find and replace text inside an existing file. Use this to make targeted changes instead of rewriting the whole file.",
        parameters={
            "path": {"type": "string", "description": "Path to the file to edit"},
            "old_string": {"type": "string", "description": "The exact text to find and replace (copy it from the file)"},
            "new_string": {"type": "string", "description": "The new text to put in its place"},
        },
        required=["path", "old_string", "new_string"],
        handler=tool_edit,
        required_permission="write",
    ))

    register_tool(ToolDef(
        name="glob",
        description="Find files by name pattern. Use this to locate files when you know part of the filename or extension. Faster than grep.",
        parameters={
            "pattern": {"type": "string", "description": "Pattern like **/*.py or **/*test* to match files"},
            "path": {"type": "string", "description": "Start searching from this directory (default: current folder)", "default": None},
        },
        required=["pattern"],
        handler=tool_glob,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="grep",
        description="Search file contents for a regex pattern. Skips .git, node_modules, __pycache__, and files > 1MB.",
        parameters={
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "include": {"type": "string", "description": "Glob filter (e.g. *.py) - always set this to narrow search!", "default": None},
            "path": {"type": "string", "description": "Directory to search in (default: current dir)", "default": "."},
            "max_size": {"type": "integer", "description": "Skip files larger than this many bytes (default: 1MB)", "default": 1000000},
            "max_matches": {"type": "integer", "description": "Stop after this many matches (default: 50)", "default": 50},
        },
        required=["pattern"],
        handler=tool_grep,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="ls",
        description="List files and folders in a directory. Use this first when exploring a new directory to see what's there.",
        parameters={
            "path": {"type": "string", "description": "Which directory to list (default: current folder ' . ')", "default": "."},
        },
        handler=tool_ls,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="tree",
        description="Show the folder/file structure of a directory as an indented tree (up to 3 levels). Use this to understand project layout at a glance.",
        parameters={
            "path": {"type": "string", "description": "Root directory to start from (default: current folder)", "default": "."},
            "depth": {"type": "integer", "description": "How many levels deep to go (default: 3, max: 5)", "default": 3},
        },
        handler=tool_tree,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="web_search",
        description="Search the internet for current information (docs, news, APIs). Use when you need info not in the local files.",
        parameters={
            "query": {"type": "string", "description": "What to search for (e.g. 'python datetime format codes')"},
            "max_results": {"type": "integer", "description": "How many results to return (default: 5)", "default": 5},
        },
        required=["query"],
        handler=tool_web_search,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="web_fetch",
        description="Fetch the text content of a webpage or API endpoint by URL.",
        parameters={
            "url": {"type": "string", "description": "Full URL to fetch (e.g. https://example.com)"},
        },
        required=["url"],
        handler=tool_web_fetch,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="shell",
        description="Run a shell command (PowerShell on Windows). Use for builds, tests, git, package mgmt, or any CLI tool. Blocked from doing destructive things (format, rm -rf /, shutdown).",
        parameters={
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout": {"type": "integer", "description": "Max seconds to wait (default: 60)", "default": 60},
        },
        required=["command"],
        handler=tool_shell,
        required_permission="full",
    ))
