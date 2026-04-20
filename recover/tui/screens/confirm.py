"""Schermata conferma dispositivo e scelta modalità."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from recover.utils.fs import BlockDevice, unmount_device

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
        if self._dev.is_mounted:
            yield Static(
                "[bold red]⚠  Il dispositivo è montato.[/bold red]\n"
                "Deve essere smontato prima di poter procedere.",
                id="mount-warning",
            )
            yield Button("Smonta ora", id="btn-unmount", variant="warning")
        yield Static("Scegli modalità di recupero:", classes="screen-title", id="mode-title")
        yield ListView(
            *[ListItem(Label(f"  {k})  {v}"), id=f"mode_{k}") for k, v in _MODES],
            id="modes",
        )
        yield Footer()

    def _device_info(self) -> str:
        dev = self._dev
        mount = dev.mountpoint if dev.is_mounted else "non montato"
        return (
            f"[bold]Dispositivo:[/bold] {dev.path}  "
            f"[bold]Label:[/bold] {dev.label or '—'}  "
            f"[bold]Size:[/bold] {dev.size}  "
            f"[bold]FS:[/bold] {dev.fstype or '?'}  "
            f"[bold]Mount:[/bold] {mount}"
        )

    def on_mount(self) -> None:
        self._update_mode_availability()

    def _update_mode_availability(self) -> None:
        lv: ListView = self.query_one("#modes")
        lv.disabled = self._dev.is_mounted
        if not self._dev.is_mounted:
            lv.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-unmount":
            return
        btn: Button = self.query_one("#btn-unmount")
        btn.disabled = True
        btn.label = "Smonto…"

        ok, err = unmount_device(self._dev)
        if ok:
            self._dev = self._dev.__class__(
                name=self._dev.name,
                path=self._dev.path,
                size=self._dev.size,
                fstype=self._dev.fstype,
                label=self._dev.label,
                mountpoint="",
                removable=self._dev.removable,
            )
            self.query_one("#device-info", Static).update(self._device_info())
            self.query_one("#mount-warning", Static).update(
                "[green]Dispositivo smontato correttamente.[/green]"
            )
            btn.remove()
            self._update_mode_availability()
            self.notify("Dispositivo smontato.", severity="information")
        else:
            self.query_one("#mount-warning", Static).update(
                f"[bold red]Smonto fallito:[/bold red] {err}"
            )
            btn.disabled = False
            btn.label = "Riprova smonto"
            self.notify(f"Errore smonto: {err}", severity="error")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self._dev.is_mounted:
            self.notify("Smonta il dispositivo prima di procedere.", severity="warning")
            return
        mode = event.item.id.replace("mode_", "") if event.item.id else ""
        self.notify(f"Modalità {mode} selezionata — prossima fase: IMAGE (non ancora implementata)", severity="information")
