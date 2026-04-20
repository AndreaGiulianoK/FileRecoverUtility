"""Schermata conferma dispositivo e scelta modalità."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import ScrollableContainer

from recover.utils.fs import BlockDevice, unmount_device
from recover.core.session import Session
from recover.tui.widgets.mode_selector import ModeSelector


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
        yield Static("Scegli modalità di recupero:", classes="screen-title")
        with ScrollableContainer():
            yield ModeSelector(id="mode-sel")
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
        sel = self.query_one(ModeSelector)
        sel.disabled = self._dev.is_mounted

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-unmount":
            return
        btn: Button = self.query_one("#btn-unmount")
        btn.disabled = True
        btn.label = "Smonto…"
        ok, err = unmount_device(self._dev)
        if ok:
            self._dev = self._dev.__class__(
                name=self._dev.name, path=self._dev.path, size=self._dev.size,
                fstype=self._dev.fstype, label=self._dev.label,
                mountpoint="", removable=self._dev.removable,
            )
            self.query_one("#device-info", Static).update(self._device_info())
            self.query_one("#mount-warning", Static).update("[green]Dispositivo smontato.[/green]")
            btn.remove()
            self.query_one(ModeSelector).disabled = False
            self.notify("Dispositivo smontato.", severity="information")
        else:
            self.query_one("#mount-warning", Static).update(
                f"[bold red]Smonto fallito:[/bold red] {err}"
            )
            btn.disabled = False
            btn.label = "Riprova smonto"
            self.notify(f"Errore smonto: {err}", severity="error")

    def on_mode_selector_mode_selected(self, event: ModeSelector.ModeSelected) -> None:
        if self._dev.is_mounted:
            self.notify("Smonta il dispositivo prima di procedere.", severity="warning")
            return
        from datetime import datetime
        from recover.utils import config as cfg_mod
        cfg = cfg_mod.load()
        session = Session(
            device=self._dev,
            mode=event.mode,
            timestamp=datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        )
        from recover.tui.screens.imaging import ImagingScreen
        self.app.push_screen(ImagingScreen(session, cfg))
