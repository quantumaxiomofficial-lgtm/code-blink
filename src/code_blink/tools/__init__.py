from code_blink.tools.registry import ToolDef, register_tool
from code_blink.tools.file_ops import (
    tool_read,
    tool_write,
    tool_edit,
    tool_glob,
    tool_grep,
    tool_ls,
)
from code_blink.tools.web_search import tool_web_search, tool_web_fetch


def register_all_tools():
    register_tool(ToolDef(
        name="read",
        description="Read the contents of a file at the given path",
        parameters={
            "path": {"type": "string", "description": "Absolute or relative path to the file"},
            "offset": {"type": "integer", "description": "Line number to start from (0-indexed)", "default": 0},
            "limit": {"type": "integer", "description": "Max characters to read", "default": 2000},
        },
        required=["path"],
        handler=tool_read,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="write",
        description="Write content to a file. Creates parent directories if needed.",
        parameters={
            "path": {"type": "string", "description": "Path to the file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        required=["path", "content"],
        handler=tool_write,
        required_permission="write",
    ))

    register_tool(ToolDef(
        name="edit",
        description="Replace text in a file. Does a single replacement.",
        parameters={
            "path": {"type": "string", "description": "Path to the file"},
            "old_string": {"type": "string", "description": "Text to replace"},
            "new_string": {"type": "string", "description": "Replacement text"},
        },
        required=["path", "old_string", "new_string"],
        handler=tool_edit,
        required_permission="write",
    ))

    register_tool(ToolDef(
        name="glob",
        description="Search for files matching a glob pattern in a directory",
        parameters={
            "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
            "path": {"type": "string", "description": "Directory to search (default: current)", "default": None},
        },
        required=["pattern"],
        handler=tool_glob,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="grep",
        description="Search file contents for a regex pattern",
        parameters={
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "include": {"type": "string", "description": "Glob filter for file types (e.g. *.py)", "default": None},
        },
        required=["pattern"],
        handler=tool_grep,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="ls",
        description="List files and directories at a given path",
        parameters={
            "path": {"type": "string", "description": "Directory path (default: current)", "default": "."},
        },
        handler=tool_ls,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="web_search",
        description="Search the web via DuckDuckGo for current information",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results to return", "default": 5},
        },
        required=["query"],
        handler=tool_web_search,
        required_permission="read",
    ))

    register_tool(ToolDef(
        name="web_fetch",
        description="Fetch and extract text content from a URL",
        parameters={
            "url": {"type": "string", "description": "URL to fetch"},
        },
        required=["url"],
        handler=tool_web_fetch,
        required_permission="read",
    ))
