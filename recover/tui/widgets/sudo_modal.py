"""Modal per inserimento password sudo."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class SudoPasswordModal(ModalScreen[str]):
    """Ritorna la password inserita, o stringa vuota se annullato."""

    DEFAULT_CSS = """
    SudoPasswordModal {
        align: center middle;
    }
    #dialog {
        width: 60;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #dialog Label {
        margin-bottom: 1;
    }
    #dialog Input {
        margin-bottom: 1;
    }
    #buttons {
        layout: horizontal;
        height: auto;
        align-horizontal: right;
    }
    #buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Annulla")]

    def compose(self) -> ComposeResult:
        with Static(id="dialog"):
            yield Label("[bold]Password richiesta[/bold]")
            yield Static(
                "ddrescue richiede privilegi per leggere il dispositivo raw.\n"
                "Inserisci la password sudo:"
            )
            yield Input(placeholder="password", password=True, id="pwd")
            with Static(id="buttons"):
                yield Button("Annulla", id="btn-cancel", variant="default")
                yield Button("OK", id="btn-ok", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#pwd", Input).focus()

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok":
            self._confirm()
        else:
            self.action_cancel()

    def _confirm(self) -> None:
        pwd = self.query_one("#pwd", Input).value
        self.dismiss(pwd)

    def action_cancel(self) -> None:
        self.dismiss("")
