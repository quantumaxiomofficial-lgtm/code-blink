from textual.widgets import Label
from datetime import datetime
from rich.markdown import Markdown
from rich.text import Text
from rich.console import Group


def _make_icon(role: str) -> Text:
    if role == "user":
        return Text("◇ ", style="#a78bfa")
    return Text("[?] ", style="bold #8b5cf6")


def _esc(text: str) -> str:
    return text.replace("[", "\[").replace("]", "\]")


class ThinkingBlock(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffer = ""
        self._ts = datetime.now().strftime("%H:%M")

    def append(self, text: str):
        self._buffer += text
        self.update(self._build_content())

    def _build_content(self):
        body = self._buffer.strip()
        header = Text.assemble(
            (" … ", "bold #7c6fa0"),
            (f"  {self._ts}", "#5b4b8a"),
            "\n",
        )
        if body:
            return Group(header, Markdown(body, code_theme="monokai"))
        return header


class StreamingText(Label):
    def __init__(self, role: str = "agent", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self._buffer = ""
        self._streaming = False
        self._ts = datetime.now().strftime("%H:%M")

    def start_stream(self):
        self._streaming = True
        self._buffer = ""
        self.update(self._build_content())

    def append_token(self, token: str):
        if not self._streaming:
            self.start_stream()
        self._buffer += token
        self.update(self._build_content())

    def finish_stream(self):
        self._streaming = False
        self.update(self._build_content())

    def _build_content(self):
        icon = _make_icon(self.role)
        header = Text.assemble(icon, (f"  {self._ts}", "#7c6fa0"), "\n")
        body = self._buffer
        if body:
            if self._streaming:
                body_text = Text(body + " ▌", style="#e2dff0")
                return Group(header, body_text)
            else:
                return Group(header, Markdown(body, code_theme="monokai"))
        return header
