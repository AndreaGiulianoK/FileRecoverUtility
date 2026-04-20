"""Schermata verifica dipendenze di sistema."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, Static

from recover.utils import deps as deps_mod


class DepsCheckScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Verifica dipendenze di sistema", id="title", classes="screen-title")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        result = deps_mod.check()

        for tool in result.ok:
            log.write(f"[green]✓[/green]  {tool}")

        for tool in result.missing:
            log.write(f"[red]✗[/red]  {tool}  [dim](non trovato)[/dim]")

        if result.all_ok:
            log.write("\n[bold green]Tutte le dipendenze sono presenti.[/bold green]")
        else:
            log.write("\n[bold red]Dipendenze mancanti. Installa con:[/bold red]")
            log.write(f"[yellow]{result.install_hint()}[/yellow]")
