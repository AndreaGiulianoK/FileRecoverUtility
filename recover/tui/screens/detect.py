"""Schermata rilevamento dispositivi."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static

from recover.utils.fs import BlockDevice, list_removable


class DetectScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Indietro"),
        Binding("r", "refresh", "Ricarica"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Dispositivi rimovibili rilevati", classes="screen-title")
        yield DataTable(id="devices", cursor_type="row")
        yield Static("", id="hint")
        yield Footer()

    def on_mount(self) -> None:
        self._load_devices()

    def _load_devices(self) -> None:
        table: DataTable = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Dispositivo", "Path", "Size", "Filesystem", "Label", "Stato")

        self._devices = list_removable()
        if not self._devices:
            self.query_one("#hint", Static).update(
                "[yellow]Nessun dispositivo rimovibile trovato.[/yellow]\n"
                "Collega una SD card o usa [bold]M[/bold] per inserire un path manuale."
            )
            return

        for dev in self._devices:
            stato = "[red]montato[/red]" if dev.is_mounted else "[green]non montato[/green]"
            table.add_row(dev.name, dev.path, dev.size, dev.fstype or "?", dev.label or "—", stato)

        self.query_one("#hint", Static).update(
            "[dim]Invio: seleziona   R: ricarica   Esc: indietro[/dim]"
        )

    def action_refresh(self) -> None:
        self._load_devices()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not self._devices:
            return
        dev = self._devices[event.cursor_row]
        from recover.tui.screens.confirm import ConfirmScreen
        self.app.push_screen(ConfirmScreen(dev))


# Schermata placeholder per le fasi non ancora implementate
class PlaceholderScreen(Screen):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"{self._title}\n\n[dim]Non ancora implementato.[/dim]", classes="screen-title")
        yield Footer()
