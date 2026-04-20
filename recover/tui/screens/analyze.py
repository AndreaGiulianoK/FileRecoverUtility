"""Schermata fase ANALYZE — recupero automatico file con TSK."""
from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, RichLog, Static, Switch

from recover.core import analyze as analyze_mod
from recover.core.session import Session


class AnalyzeScreen(Screen):
    BINDINGS = [Binding("escape", "abort", "Interrompi", show=True)]

    DEFAULT_CSS = """
    #instructions { margin: 0 1 1 1; }
    #options { height: auto; margin: 0 1 1 1; }
    #options Switch { margin-right: 1; }
    #progress { margin: 1 1 0 1; }
    #log { margin: 1 1; border: solid $panel; height: 1fr; }
    """

    def __init__(self, session: Session, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._session = session
        self._cfg = app_cfg
        self._abort = asyncio.Event()
        self._running = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Fase 5A — Recupero file (TSK)", classes="screen-title")
        yield Static(
            f"[dim]Immagine:[/dim] {self._session.image_path}\n"
            "Recupero automatico: i file cancellati vengono estratti con nome e "
            "struttura cartelle originali.",
            id="instructions",
        )
        with Horizontal(id="options"):
            yield Switch(value=True, id="sw-all", animate=False)
            yield Label("Includi anche i file non cancellati (attivo di default)")
        yield Button("Avvia recupero", id="btn-launch", variant="primary")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#progress", ProgressBar).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-launch":
                self.query_one("#btn-launch", Button).disabled = True
                self.query_one("#sw-all", Switch).disabled = True
                self.query_one("#progress", ProgressBar).display = True
                self._run_recovery()
            case "btn-back":
                self.app.pop_screen()

    @work(exclusive=True)
    async def _run_recovery(self) -> None:
        log = self.query_one("#log", RichLog)
        bar = self.query_one("#progress", ProgressBar)
        include_all = self.query_one("#sw-all", Switch).value

        missing = analyze_mod.check_tools()
        if missing:
            log.write(f"[red]Strumenti TSK mancanti: {', '.join(missing)}[/]")
            log.write("[yellow]Installa con: sudo apt install sleuthkit[/]")
            self.mount(Button("Torna indietro", id="btn-back", variant="error"))
            return

        raw_dir = self._session.session_dir / "raw_tsk"
        raw_dir.mkdir(parents=True, exist_ok=True)
        self._session.raw_dir = raw_dir
        self._running = True

        log.write("[dim]Scansione filesystem con fls…[/]")

        prog = analyze_mod.AnalyzeProgress()
        async for prog in analyze_mod.run(
            self._session.image_path,
            raw_dir,
            include_all=include_all,
            abort=self._abort,
        ):
            if prog.finished:
                break
            if prog.done == 0:
                if prog.total == 0:
                    log.write("[yellow]Nessun file trovato nel filesystem.[/]")
                    break
                kind = "file (cancellati + esistenti)" if include_all else "file cancellati"
                log.write(f"[cyan]Trovati [bold]{prog.total}[/bold] {kind}.[/]")
            else:
                bar.progress = prog.done * 100 / prog.total
                if prog.done % 100 == 0 or prog.done == prog.total:
                    fail_str = f"  ({prog.failed} falliti)" if prog.failed else ""
                    log.write(f"[dim]{prog.done}/{prog.total}[/]{fail_str}")

        self._running = False

        if self._abort.is_set():
            log.write("[yellow]Recupero interrotto dall'utente.[/]")
            return

        bar.progress = 100
        recovered = [f for f in raw_dir.rglob("*") if f.is_file()]
        log.write("")
        if recovered:
            log.write(f"[bold green]Estratti {len(recovered)} file.[/]")
            if prog.failed:
                log.write(
                    f"[yellow]{prog.failed} file non recuperabili "
                    "(settori danneggiati o sovritti).[/]"
                )
            from recover.tui.screens.organize import OrganizeScreen
            self.app.switch_screen(OrganizeScreen(self._session, self._cfg))
        else:
            log.write(
                "[red]Nessun file recuperato.[/]\n"
                "Il filesystem potrebbe essere corrotto: prova la [bold]modalità B[/bold] (photorec)."
            )
            self.mount(Button("Torna indietro", id="btn-back", variant="error"))

    def action_abort(self) -> None:
        if not self._running:
            self.app.pop_screen()
            return
        self._abort.set()
        self.notify("Recupero interrotto…", severity="warning")

    def on_unmount(self) -> None:
        self._abort.set()
