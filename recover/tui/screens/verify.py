"""Schermata fase VERIFY — fsck + SHA-256."""
from __future__ import annotations

from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RichLog, Static

from recover.core import verify as verify_mod
from recover.core.session import Session


class VerifyScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 4 — Verifica immagine (fsck + SHA-256)", classes="screen-title")
        yield Static("", id="result")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Static("", id="nav-hint")
        yield Footer()

    def on_mount(self) -> None:
        self._run_verify()

    @work(exclusive=True)
    async def _run_verify(self) -> None:
        import asyncio
        log: RichLog = self.query_one("#log")
        result_lbl: Static = self.query_one("#result")

        assert self._session.image_path is not None

        log.write(f"[cyan]Immagine:[/] {self._session.image_path}")

        # SHA-256 (in thread per non bloccare la UI)
        log.write("[dim]Calcolo SHA-256…[/]")
        sha_path = self._session.image_path.with_suffix(".sha256")
        loop = asyncio.get_event_loop()
        digest = await loop.run_in_executor(
            None, verify_mod.compute_sha256, self._session.image_path, sha_path
        )
        self._session.image_sha256 = digest
        log.write(f"[green]SHA-256:[/] {digest}")

        # fsck
        log.write("[dim]Esecuzione fsck -n…[/]")
        ok, output = await loop.run_in_executor(
            None, verify_mod.run_fsck, self._session.image_path
        )
        self._session.fsck_ok = ok
        self._session.fsck_output = output
        for line in output.splitlines():
            log.write(line)

        # versioni tool
        for tool in ("ddrescue", "testdisk", "photorec", "exiftool"):
            self._session.tool_versions[tool] = verify_mod.get_tool_version(tool)

        if ok:
            result_lbl.update("[green]Filesystem integro.[/green]")
        else:
            result_lbl.update("[yellow]Filesystem con errori — potrebbe richiedere carving raw.[/yellow]")

        self._show_navigation(ok)

    def _show_navigation(self, fs_ok: bool) -> None:
        hint: Static = self.query_one("#nav-hint")
        mode = self._session.mode
        if mode == "C":
            hint.update("[green]Modalità C — imaging completato.[/green]")
            self.mount(Button("Fine", id="btn-done", variant="success"))
        elif mode == "A":
            label = "Procedi con testdisk (recupero file cancellati)"
            if not fs_ok:
                label += "  [yellow](filesystem con errori — potrebbe avere problemi)[/yellow]"
            hint.update(label)
            self.mount(Button("Avvia testdisk", id="btn-analyze", variant="primary"))
            if not fs_ok:
                self.mount(Button("Usa photorec invece", id="btn-carve", variant="warning"))
        else:
            hint.update("Procedi con photorec (carving raw)")
            self.mount(Button("Avvia photorec", id="btn-carve", variant="primary"))
            if fs_ok:
                self.mount(Button("Usa testdisk invece", id="btn-analyze", variant="default"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-done":
                self.app.pop_screen()
                self.app.pop_screen()
                self.app.pop_screen()
            case "btn-analyze":
                from recover.tui.screens.analyze import AnalyzeScreen
                self.app.switch_screen(AnalyzeScreen(self._session, self._cfg))
            case "btn-carve":
                from recover.tui.screens.carve import CarveScreen
                self.app.switch_screen(CarveScreen(self._session, self._cfg))
