"""Schermata fase IMAGE — ddrescue con barra progresso."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, RichLog, Static

from recover.core import imaging as imaging_mod
from recover.core.session import Session
from recover.utils import config as cfg_mod
from recover.utils.fs import session_dir


class ImagingScreen(Screen):
    BINDINGS = [Binding("escape", "abort", "Interrompi", show=True)]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg
        self._aborted = False
        self._total_bytes = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 3 — Imaging disco (ddrescue)", classes="screen-title")
        yield Static("", id="stats-line")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._prepare_paths()
        self._ask_password()

    def _prepare_paths(self) -> None:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._session.timestamp = ts

        img_dir = cfg_mod.image_dir(self._cfg)
        img_dir.mkdir(parents=True, exist_ok=True)

        dev = self._session.device
        label = dev.label or dev.name
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        base_name = f"{safe}_{ts}"

        self._session.image_path = img_dir / f"{base_name}.img"
        self._session.map_path   = img_dir / f"{base_name}.map"

        base_out = cfg_mod.output_dir(self._cfg)
        self._session.session_dir = session_dir(base_out, dev, ts)
        self._session.session_dir.mkdir(parents=True, exist_ok=True)

        self._total_bytes = imaging_mod.device_size_bytes(dev.path)

    def _ask_password(self, error: str = "") -> None:
        from recover.tui.widgets.sudo_modal import SudoPasswordModal
        self.app.push_screen(SudoPasswordModal(error=error), self._on_password)

    def _on_password(self, password: str) -> None:
        if not password:
            self.notify("Password non inserita — imaging annullato.", severity="warning")
            self.app.pop_screen()
            return
        self._validate_and_start(password)

    @work(exclusive=True)
    async def _validate_and_start(self, password: str) -> None:
        log: RichLog = self.query_one("#log")
        log.write("[dim]Verifica password sudo…[/]")

        ok = await imaging_mod.validate_sudo(password)
        if not ok:
            log.write("[red]Password errata.[/]")
            self._ask_password(error="Password errata, riprova.")
            return

        log.write("[green]Autenticazione OK.[/]")
        self._start_imaging()

    @work(exclusive=True)
    async def _start_imaging(self) -> None:
        log: RichLog = self.query_one("#log")
        stats: Static = self.query_one("#stats-line")
        bar: ProgressBar = self.query_one("#progress")

        extra = self._cfg.get("imaging", {}).get("ddrescue_extra_args", "").split()
        extra = [a for a in extra if a]

        log.write(f"[cyan]Sorgente:[/] {self._session.device.path}")
        log.write(f"[cyan]Immagine:[/] {self._session.image_path}")
        log.write(f"[cyan]Mapfile:[/]  {self._session.map_path}")
        log.write("[dim]Avvio ddrescue…[/]")

        assert self._session.image_path is not None
        assert self._session.map_path is not None

        async for prog in imaging_mod.run(
            Path(self._session.device.path),
            self._session.image_path,
            self._session.map_path,
            extra_args=extra,
        ):
            if self._aborted:
                break
            if prog.line:
                log.write(prog.line)

            if self._total_bytes > 0:
                bar.progress = min(100, int(prog.rescued_bytes * 100 / self._total_bytes))

            stats.update(
                f"Recuperati: [green]{_human(prog.rescued_bytes)}[/]  "
                f"Errori: [{'red' if prog.errors else 'green'}]{prog.errors}[/]  "
                f"Velocità: {prog.rate}  Elapsed: {prog.elapsed}"
            )

        if not self._aborted:
            log.write("[green]Imaging completato.[/]")
            self._go_next()

    def _go_next(self) -> None:
        from recover.tui.screens.verify import VerifyScreen
        self.app.switch_screen(VerifyScreen(self._session, self._cfg))

    def action_abort(self) -> None:
        self._aborted = True
        self.notify("Imaging interrotto.", severity="warning")
        self.app.pop_screen()


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.0f} TB"
