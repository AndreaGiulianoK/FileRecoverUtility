"""App Textual principale."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from recover.tui.screens.main_menu import MainMenuScreen

CSS = """
Screen {
    background: $surface;
}

.screen-title {
    padding: 1 2;
    color: $accent;
    text-style: bold;
}

#menu {
    margin: 2 4;
    width: 60;
}

#devices {
    margin: 1 2;
    height: 1fr;
}

#device-info {
    margin: 1 2;
    padding: 1;
    border: solid $accent;
}

#log {
    margin: 1 2;
    height: 1fr;
    border: solid $panel;
}

#hint {
    margin: 0 2;
    padding: 0 1;
    color: $text-muted;
}

#progress {
    margin: 0 2 1 2;
}

#stats-line {
    margin: 0 2;
    padding: 0 1;
}

#progress-label {
    margin: 0 2;
    color: $text-muted;
}

#result {
    margin: 1 2;
    padding: 1;
    text-style: bold;
}

#nav-hint {
    margin: 0 2 1 2;
}

#mount-warning {
    margin: 0 2;
    padding: 1;
    color: $error;
}

#instructions {
    margin: 1 2;
    padding: 1;
    border: solid $panel;
    height: auto;
}

#summary {
    margin: 1 2;
    padding: 1;
    border: solid $success;
    height: auto;
}

Button {
    margin: 0 2 1 2;
}
"""


class RecoverApp(App):
    TITLE = "RECOVER"
    SUB_TITLE = "File Recovery Utility v0.1"
    CSS = CSS
    BINDINGS = [
        Binding("q", "quit", "Esci", show=True),
    ]

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
