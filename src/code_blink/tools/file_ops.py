from __future__ import annotations
from pathlib import Path


async def tool_read(path: str, offset: int = 0, limit: int = 2000) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if not p.is_file():
        return f"Error: not a file: {path}"
    try:
        content = p.read_text(encoding="utf-8")
        if offset:
            lines = content.splitlines()
            content = "\n".join(lines[offset:])
        if limit and len(content) > limit:
            content = content[:limit] + f"\n... (truncated at {limit} chars)"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


async def tool_write(path: str, content: str) -> str:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def tool_edit(path: str, old_string: str, new_string: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    try:
        content = p.read_text(encoding="utf-8")
        if old_string not in content:
            return f"Error: string not found in {path}"
        count = content.count(old_string)
        content = content.replace(old_string, new_string, 1)
        p.write_text(content, encoding="utf-8")
        return f"Replaced 1 occurrence in {path} ({len(new_string)} chars written)"
    except Exception as e:
        return f"Error editing file: {e}"


async def tool_glob(pattern: str, path: str | None = None) -> str:
    search_path = Path(path) if path else Path.cwd()
    if not search_path.exists():
        return f"Error: directory not found: {path}"
    try:
        matches = list(search_path.rglob(pattern))
        if not matches:
            return f"No files matching '{pattern}'"
        lines = [str(m.relative_to(search_path)) for m in matches[:100]]
        if len(matches) > 100:
            lines.append(f"... and {len(matches) - 100} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching files: {e}"


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".env", ".idea", ".vscode", ".hg", ".svn"}
MAX_FILE_SIZE = 1_000_000  # 1MB


async def tool_grep(
    pattern: str,
    include: str | None = None,
    path: str = ".",
    max_size: int = MAX_FILE_SIZE,
    max_matches: int = 50,
) -> str:
    import re
    search_path = Path(path)
    if not search_path.exists():
        return f"Error: path not found: {path}"
    try:
        matches = []
        files = list(search_path.rglob(include or "*"))
        for f in files:
            if not f.is_file():
                continue
            # Skip hidden dirs and binary dirs
            parts = f.relative_to(search_path).parts
            if any(p in SKIP_DIRS for p in parts):
                continue
            if f.stat().st_size > max_size:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        rel = f.relative_to(search_path)
                        matches.append(f"{rel}:{i}: {line[:200]}")
                        if len(matches) >= max_matches:
                            break
            except Exception:
                continue
            if len(matches) >= max_matches:
                break
        if not matches:
            return f"No matches for '{pattern}' in {path}"
        result = "\n".join(matches)
        return result
    except Exception as e:
        return f"Error searching content: {e}"


async def tool_ls(path: str = ".") -> str:
    p = Path(path)
    if not p.exists():
        return f"Error: path not found: {path}"
    if p.is_file():
        return f"{p.name} ({p.stat().st_size} bytes)"
    try:
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for e in entries:
            if e.is_dir():
                lines.append(f"  {e.name}/")
            else:
                lines.append(f"  {e.name} ({e.stat().st_size} bytes)")
        return f"Contents of {path}/:\n" + "\n".join(lines[:50]) + (f"\n... ({len(entries)} entries)" if len(entries) > 50 else "")
    except Exception as e:
        return f"Error listing directory: {e}"


async def tool_tree(path: str = ".", depth: int = 3) -> str:
    """Display a directory tree up to `depth` levels deep."""
    p = Path(path)
    if not p.exists():
        return f"Error: path not found: {path}"
    if not p.is_dir():
        return f"{p.name} (file, {p.stat().st_size} bytes)"

    lines = [f"{p.name}/"]
    try:
        def walk(dir_path: Path, prefix: str = "", remaining: int = depth):
            if remaining <= 0:
                return
            try:
                entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except OSError:
                lines.append(f"{prefix}! (access denied)")
                return
            for i, e in enumerate(entries):
                if e.name.startswith("."):
                    continue
                try:
                    is_dir = e.is_dir()
                except OSError:
                    lines.append(f"{prefix}|-- {e.name} (?)")
                    continue
                is_last = i == len(entries) - 1
                connector = "`-- " if is_last else "|-- "
                lines.append(f"{prefix}{connector}{e.name}{'/' if is_dir else ''}")
                if is_dir:
                    extension = "    " if is_last else "|   "
                    walk(e, prefix + extension, remaining - 1)
        walk(p)
        return "\n".join(lines[:200])
    except Exception as e:
        return f"Error building tree: {e}"
