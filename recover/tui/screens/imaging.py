"""Schermata fase IMAGE — ddrescue con barra progresso e log live."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ProgressBar, RichLog, Static

from recover.core import imaging as imaging_mod
from recover.core.session import Session
from recover.utils import config as cfg_mod
from recover.utils.fs import session_dir


class ImagingScreen(Screen):
    BINDINGS = [Binding("escape", "abort", "Interrompi", show=True)]

    DEFAULT_CSS = """
    #stats-box {
        height: auto;
        border: solid $panel;
        margin: 0 1;
        padding: 0 1;
    }
    #stat-rescued { color: $success; }
    #stat-errors  { color: $error; }
    #stat-rate    { color: $accent; }
    #stat-elapsed { color: $text-muted; }
    #progress     { margin: 1 1 0 1; }
    #log          { margin: 1 1; border: solid $panel; height: 1fr; }
    """

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg
        self._aborted = False
        self._total_bytes = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 3 — Imaging disco (ddrescue)", classes="screen-title")
        with Vertical(id="stats-box"):
            yield Label("Recuperati: —", id="stat-rescued")
            yield Label("Errori:  —", id="stat-errors")
            yield Label("Velocità: —", id="stat-rate")
            yield Label("Elapsed: —", id="stat-elapsed")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
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
        log = self.query_one("#log", RichLog)
        log.write("[dim]Verifica credenziali sudo…[/]")
        ok = await imaging_mod.validate_sudo(password)
        if not ok:
            log.write("[red]Password sudo errata.[/]")
            self._ask_password(error="Password errata, riprova.")
            return
        log.write("[green]Credenziali OK.[/]")
        self._start_imaging()

    @work(exclusive=True)
    async def _start_imaging(self) -> None:
        log = self.query_one("#log", RichLog)
        bar = self.query_one("#progress", ProgressBar)

        extra = [a for a in self._cfg.get("imaging", {}).get("ddrescue_extra_args", "").split() if a]

        log.write("")
        log.write(f"[cyan]Sorgente :[/] {self._session.device.path}")
        log.write(f"[cyan]Immagine  :[/] {self._session.image_path}")
        log.write(f"[cyan]Mapfile   :[/] {self._session.map_path}")
        if self._total_bytes:
            log.write(f"[cyan]Dimensione:[/] {_human(self._total_bytes)}")
        log.write("")
        log.write("[dim]━━━ Output ddrescue ━━━[/]")

        assert self._session.image_path is not None
        assert self._session.map_path is not None

        last_info = ""
        async for prog in imaging_mod.run(
            Path(self._session.device.path),
            self._session.image_path,
            self._session.map_path,
            extra_args=extra,
        ):
            if self._aborted:
                break

            # logga solo righe informative non duplicate
            if prog.info_line and prog.info_line != last_info:
                log.write(prog.info_line)
                last_info = prog.info_line

            # preferisci pct_rescued calcolata da ddrescue, fallback su bytes/total
            if prog.pct_rescued > 0:
                bar.progress = min(100, prog.pct_rescued)
            elif self._total_bytes > 0:
                bar.progress = min(100, prog.rescued_bytes * 100 / self._total_bytes)

            rescued_str = _human(prog.rescued_bytes)
            total_str = f" / {_human(self._total_bytes)}" if self._total_bytes else ""
            pct_str = f"  ({prog.pct_rescued:.1f}%)" if prog.pct_rescued > 0 else ""
            self.query_one("#stat-rescued", Label).update(
                f"Recuperati: [bold]{rescued_str}{total_str}[/]{pct_str}"
            )
            self.query_one("#stat-errors", Label).update(
                f"Errori:     [bold]{prog.errors}[/]"
                + (f"  ({_human(prog.error_bytes)} non leggibili)" if prog.error_bytes else "")
            )
            rate_str = prog.rate or "—"
            avg_str = prog.avg_rate or "—"
            rem_str = f"  ETA: {prog.remaining}" if prog.remaining and prog.remaining != "n/a" else ""
            self.query_one("#stat-rate", Label).update(
                f"Velocità:   {rate_str}  (media: {avg_str}){rem_str}"
            )
            self.query_one("#stat-elapsed", Label).update(
                f"Elapsed:    {prog.elapsed or '—'}"
            )

        if not self._aborted:
            log.write("")
            log.write("[bold green]Imaging completato.[/]")
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
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"
