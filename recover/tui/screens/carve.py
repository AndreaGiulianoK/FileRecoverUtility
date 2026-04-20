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

    def _find_output(self, raw: Path) -> tuple[Path, list[Path]]:
        """Cerca i file recuperati da photorec.

        photorec crea recup_dir.N/ nell'output dir scelto dall'utente,
        che può essere raw_photorec/ oppure session_dir/ direttamente.
        """
        files = [f for f in raw.rglob("*") if f.is_file()]
        if files:
            return raw, files

        # fallback: recup_dir.* creati direttamente in session_dir
        assert self._session.session_dir is not None
        all_files: list[Path] = []
        for d in sorted(self._session.session_dir.glob("recup_dir.*")):
            all_files.extend(f for f in d.rglob("*") if f.is_file())
        if all_files:
            return self._session.session_dir, all_files

        return raw, []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
            self.app.pop_screen()
            self.app.pop_screen()
            return
        if event.button.id not in ("btn-launch", "btn-retry"):
            return
        raw = self._raw_dir()
        raw.mkdir(parents=True, exist_ok=True)
        self._session.raw_dir = raw

        assert self._session.image_path is not None
        with self.app.suspend():
            subprocess.run(["photorec", str(self._session.image_path)])

        raw, files = self._find_output(raw)
        if files:
            self._session.raw_dir = raw
            self.notify(f"{len(files)} file trovati.", severity="information")
            from recover.tui.screens.organize import OrganizeScreen
            self.app.switch_screen(OrganizeScreen(self._session, self._cfg))
        else:
            self.notify("Nessun file trovato. Verifica la cartella di output in photorec.", severity="warning")
            self.mount(Button("Riprova photorec", id="btn-retry", variant="warning"))
            self.mount(Button("Annulla — torna al menu", id="btn-cancel", variant="error"))
