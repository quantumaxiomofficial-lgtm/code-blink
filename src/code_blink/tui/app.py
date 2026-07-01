from textual.app import App
from textual.binding import Binding

from code_blink.config.schema import AppConfig
from code_blink.tui.chat_screen import ChatScreen


class CodeBlinkApp(App):
    TITLE = "Code Blink"
    SUB_TITLE = "local-first AI coding agent"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_screen", "Clear"),
    ]

    def __init__(self, config: AppConfig):
        super().__init__()
        self.blink_config = config

    def on_mount(self):
        self.push_screen(ChatScreen(self.blink_config))

    def action_clear_screen(self):
        screen = self.screen
        if isinstance(screen, ChatScreen):
            screen.clear_messages()
