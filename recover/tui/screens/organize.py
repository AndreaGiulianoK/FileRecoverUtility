"""Schermata fase ORGANIZE — rinomina, dedup, sorting."""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, RichLog, Static

from recover.core import organize as organize_mod
from recover.core.session import Session


class OrganizeScreen(Screen):
    BINDINGS = [Binding("escape", "abort", "Interrompi")]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg
        self._abort = threading.Event()
        self._running = False

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
        log = self.query_one("#log", RichLog)
        bar = self.query_one("#progress", ProgressBar)
        label = self.query_one("#progress-label", Static)

        raw_dir = self._session.raw_dir
        session_dir = self._session.session_dir
        if raw_dir is None or session_dir is None:
            log.write("[red]Errore: percorsi sessione non configurati.[/]")
            return

        log.write(f"[cyan]Sorgente raw:[/] {raw_dir}")
        log.write(f"[cyan]Destinazione:[/] {session_dir}")
        self._running = True

        def progress_cb(done: int, total: int, name: str) -> None:
            pct = int(done * 100 / total) if total else 0
            bar.progress = pct
            label.update(f"[{done}/{total}] {name}")

        abort_ref = self._abort
        loop = asyncio.get_event_loop()

        def _run_sync():
            return list(organize_mod.run(raw_dir, session_dir, self._cfg, progress_cb, abort_ref))

        recovered = await loop.run_in_executor(None, _run_sync)
        self._running = False

        if self._abort.is_set():
            log.write(f"[yellow]Interrotto dopo {len(recovered)} file.[/]")
            return

        self._session.recovered_files = recovered
        bar.progress = 100
        log.write(f"[green]Completato:[/] {len(recovered)} file processati.")

        from recover.tui.screens.report_done import ReportDoneScreen
        self.app.switch_screen(ReportDoneScreen(self._session, self._cfg))

    def action_abort(self) -> None:
        if self._running:
            self._abort.set()
            self.notify("Organizzazione interrotta.", severity="warning")
        self.app.pop_screen()

    def on_unmount(self) -> None:
        self._abort.set()
