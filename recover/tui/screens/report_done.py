"""Schermata fase REPORT — generazione HTML e riepilogo finale."""
from __future__ import annotations

import subprocess
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RichLog, Static

from recover.core import report as report_mod
from recover.core.session import Session


class ReportDoneScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Indietro"),
        Binding("q", "app.quit", "Esci"),
    ]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg
        self._report_path = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 7 — Report e riepilogo finale", classes="screen-title")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Static("", id="summary")
        yield Footer()

    def on_mount(self) -> None:
        self._generate()

    @work(exclusive=True)
    async def _generate(self) -> None:
        import asyncio
        log: RichLog = self.query_one("#log")
        summary: Static = self.query_one("#summary")

        log.write("[dim]Generazione report HTML…[/]")
        loop = asyncio.get_event_loop()
        report_path = await loop.run_in_executor(None, report_mod.generate, self._session)
        self._report_path = report_path
        log.write(f"[green]Report:[/] {report_path}")

        files = self._session.recovered_files
        dup_count = sum(1 for f in files if f.status == "DUPLICATO")
        img_count = sum(1 for f in files if f.mimetype.startswith("image/"))
        vid_count = sum(1 for f in files if f.mimetype.startswith("video/"))

        summary.update(
            f"\n[bold green]Recupero completato![/bold green]\n\n"
            f"  Totale file:    [green]{len(files)}[/]\n"
            f"  Immagini:       {img_count}\n"
            f"  Video:          {vid_count}\n"
            f"  Duplicati:      {dup_count}\n"
            f"  Output:         [cyan]{self._session.session_dir}[/]\n"
            f"  Report HTML:    [cyan]{report_path}[/]\n"
        )

        await self.mount(Button("Apri report nel browser", id="btn-open", variant="success"))
        await self.mount(Button("Apri cartella output", id="btn-folder", variant="default"))
        await self.mount(Button("Esci", id="btn-quit", variant="error"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-open" if self._report_path:
                subprocess.Popen(["xdg-open", str(self._report_path)])
            case "btn-folder" if self._session.session_dir:
                subprocess.Popen(["xdg-open", str(self._session.session_dir)])
            case "btn-quit":
                self.app.exit()
