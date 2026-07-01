from textual.widgets import Label
import difflib


def _esc(text: str) -> str:
    return text.replace("[", "\[").replace("]", "\]")


def compute_diff(old_content: str, new_content: str, file_path: str = "") -> str:
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"old/{file_path}" if file_path else "old",
        tofile=f"new/{file_path}" if file_path else "new",
        lineterm="",
    )
    lines = []
    for line in diff:
        content = _esc(line)
        if line.startswith("---") or line.startswith("+++"):
            lines.append(f"[bold #7c6fa0]{content}[/]")
        elif line.startswith("@@"):
            lines.append(f"[#5b4b8a]{content}[/]")
        elif line.startswith("-"):
            lines.append(f"[#f87171]{content}[/]")
        elif line.startswith("+"):
            lines.append(f"[#4ade80]{content}[/]")
        else:
            lines.append(f"[#a1a1aa]{content}[/]")
    return "\n".join(lines)


class DiffBlock(Label):
    def __init__(self, old: str, new: str, path: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old = old
        self._new = new
        self._path = path
        self.update(self._build_content())

    def _build_content(self):
        diff_text = compute_diff(self._old, self._new, self._path)
        header = f"[bold #a78bfa]  {self._path or 'file'}[/]"
        return f"{header}\n{diff_text}"
