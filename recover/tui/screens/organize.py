"""Schermata fase ORGANIZE — rinomina, dedup, sorting."""
from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, RichLog, Static

from recover.core import organize as organize_mod
from recover.core.session import Session


class OrganizeScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 6 — Organizzazione file (EXIF rename, dedup, sorting)", classes="screen-title")
        yield Static("", id="progress-label")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._run_organize()

    @work(exclusive=True)
    async def _run_organize(self) -> None:
        log: RichLog = self.query_one("#log")
        bar: ProgressBar = self.query_one("#progress")
        label: Static = self.query_one("#progress-label")

        raw_dir = self._session.raw_dir
        session_dir = self._session.session_dir

        if raw_dir is None or session_dir is None:
            log.write("[red]Errore: percorsi sessione non configurati.[/]")
            return

        log.write(f"[cyan]Sorgente raw:[/] {raw_dir}")
        log.write(f"[cyan]Destinazione:[/] {session_dir}")

        def progress_cb(done: int, total: int, name: str) -> None:
            pct = int(done * 100 / total) if total else 0
            bar.progress = pct
            label.update(f"[{done}/{total}] {name}")

        loop = asyncio.get_event_loop()

        def _run_sync():
            files = list(organize_mod.run(raw_dir, session_dir, self._cfg, progress_cb))
            return files

        recovered = await loop.run_in_executor(None, _run_sync)
        self._session.recovered_files = recovered

        bar.progress = 100
        log.write(f"[green]Organizzazione completata:[/] {len(recovered)} file processati.")

        from recover.tui.screens.report_done import ReportDoneScreen
        self.app.switch_screen(ReportDoneScreen(self._session, self._cfg))
