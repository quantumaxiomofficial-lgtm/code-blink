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


async def tool_grep(pattern: str, include: str | None = None) -> str:
    search_path = Path.cwd()
    try:
        import re
        matches = []
        files = list(search_path.rglob("*")) if not include else list(search_path.rglob(include))
        for f in files:
            if not f.is_file():
                continue
            try:
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    if re.search(pattern, line):
                        rel = f.relative_to(search_path)
                        matches.append(f"{rel}:{i}: {line[:200]}")
            except Exception:
                continue
            if len(matches) >= 100:
                break
        if not matches:
            return f"No matches for '{pattern}'"
        return "\n".join(matches[:100])
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
