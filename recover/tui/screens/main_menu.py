"""Schermata menu principale."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView

from recover.utils import deps as deps_mod


class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Esci"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Label("  Nuovo recupero"), id="new"),
            ListItem(Label("  Riprendi sessione"), id="resume"),
            ListItem(Label("  Configurazione"), id="config"),
            ListItem(Label("  Verifica dipendenze"), id="deps"),
            id="menu",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        match event.item.id:
            case "new":
                from recover.tui.screens.detect import DetectScreen
                self.app.push_screen(DetectScreen())
            case "resume":
                from recover.utils import config as cfg_mod
                from recover.tui.screens.resume import ResumeScreen
                self.app.push_screen(ResumeScreen(cfg_mod.load()))
            case "deps":
                from recover.tui.screens.deps_check import DepsCheckScreen
                self.app.push_screen(DepsCheckScreen())
            case "config":
                self.notify("Non ancora implementato", severity="warning")
