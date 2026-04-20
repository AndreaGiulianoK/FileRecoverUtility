"""Schermata fase ANALYZE — lancia testdisk interattivo."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from recover.core.session import Session


class AnalyzeScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 5A — Recupero file cancellati (testdisk)", classes="screen-title")
        yield Static(
            "testdisk è un programma interattivo.\n"
            "Premi [bold]Avvia testdisk[/bold]: il terminale passerà a testdisk.\n\n"
            f"[dim]Immagine:[/dim] {self._session.image_path}\n\n"
            "In testdisk:\n"
            "  1. Seleziona la partizione\n"
            "  2. Scegli [bold]Advanced → Undelete[/bold]\n"
            "  3. Copia i file recuperati nella cartella:\n"
            f"     [green]{self._raw_dir()}[/green]\n"
            "  4. Esci da testdisk (Q)\n\n"
            "Dopo aver chiuso testdisk, l'utility riprenderà automaticamente.",
            id="instructions",
        )
        yield Button("Avvia testdisk", id="btn-launch", variant="primary")
        yield Footer()

    def _raw_dir(self) -> Path:
        assert self._session.session_dir is not None
        return self._session.session_dir / "raw_testdisk"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-launch":
            return
        raw = self._raw_dir()
        raw.mkdir(parents=True, exist_ok=True)
        self._session.raw_dir = raw

        assert self._session.image_path is not None
        with self.app.suspend():
            subprocess.run(["testdisk", str(self._session.image_path)])

        # dopo il ritorno, verifica se ci sono file recuperati
        files = list(raw.rglob("*"))
        recovered = [f for f in files if f.is_file()]
        if recovered:
            self.notify(f"{len(recovered)} file trovati. Procedo con organizzazione.", severity="information")
            from recover.tui.screens.organize import OrganizeScreen
            self.app.switch_screen(OrganizeScreen(self._session, self._cfg))
        else:
            self.notify(
                "Nessun file trovato nella cartella raw. "
                "Verifica di aver copiato i file in testdisk.",
                severity="warning",
            )
