"""Schermata fase CARVE — lancia photorec interattivo."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from recover.core.session import Session


class CarveScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 5B — Recupero file carving raw (photorec)", classes="screen-title")
        yield Static(
            "photorec è un programma interattivo.\n"
            "Premi [bold]Avvia photorec[/bold]: il terminale passerà a photorec.\n\n"
            f"[dim]Immagine:[/dim] {self._session.image_path}\n\n"
            "In photorec:\n"
            "  1. Seleziona la partizione (o [bold]Whole disk[/bold])\n"
            "  2. Scegli il filesystem (Other per FAT/exFAT corrotto)\n"
            "  3. Seleziona la cartella di output:\n"
            f"     [green]{self._raw_dir()}[/green]\n"
            "  4. Avvia la scansione\n\n"
            "Dopo aver chiuso photorec, l'utility riprenderà automaticamente.",
            id="instructions",
        )
        yield Button("Avvia photorec", id="btn-launch", variant="primary")
        yield Footer()

    def _raw_dir(self) -> Path:
        assert self._session.session_dir is not None
        return self._session.session_dir / "raw_photorec"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-launch":
            return
        raw = self._raw_dir()
        raw.mkdir(parents=True, exist_ok=True)
        self._session.raw_dir = raw

        assert self._session.image_path is not None
        with self.app.suspend():
            subprocess.run(["photorec", str(self._session.image_path)])

        files = [f for f in raw.rglob("*") if f.is_file()]
        if files:
            self.notify(f"{len(files)} file trovati. Procedo con organizzazione.", severity="information")
            from recover.tui.screens.organize import OrganizeScreen
            self.app.switch_screen(OrganizeScreen(self._session, self._cfg))
        else:
            self.notify(
                "Nessun file trovato. Verifica la cartella di output scelta in photorec.",
                severity="warning",
            )
