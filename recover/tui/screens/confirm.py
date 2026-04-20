"""Schermata conferma dispositivo e scelta modalità."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from recover.utils.fs import BlockDevice

_MODES = [
    ("A", "Recupero file cancellati  (filesystem leggibile)"),
    ("B", "Recupero filesystem corrotto  (carving raw)"),
    ("C", "Solo imaging  (crea immagine .img e ferma)"),
]


class ConfirmScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, device: BlockDevice) -> None:
        super().__init__()
        self._dev = device

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self._device_info(), id="device-info")
        yield Static("Scegli modalità di recupero:", classes="screen-title")
        yield ListView(
            *[ListItem(Label(f"  {k})  {v}"), id=f"mode_{k}") for k, v in _MODES],
            id="modes",
        )
        yield Footer()

    def _device_info(self) -> str:
        dev = self._dev
        mount = dev.mountpoint if dev.is_mounted else "non montato"
        warn = "\n[bold red]⚠ ATTENZIONE: dispositivo montato. Smonta prima di procedere.[/bold red]" if dev.is_mounted else ""
        return (
            f"[bold]Dispositivo:[/bold] {dev.path}  "
            f"[bold]Label:[/bold] {dev.label or '—'}  "
            f"[bold]Size:[/bold] {dev.size}  "
            f"[bold]FS:[/bold] {dev.fstype or '?'}  "
            f"[bold]Mount:[/bold] {mount}"
            f"{warn}"
        )

    def on_mount(self) -> None:
        self.query_one(ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        mode = event.item.id.replace("mode_", "") if event.item.id else ""
        self.notify(f"Modalità {mode} selezionata — prossima fase: IMAGE (non ancora implementata)", severity="information")
