"""Modal per inserimento password sudo."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class SudoPasswordModal(ModalScreen[str]):
    """Ritorna la password inserita, o stringa vuota se annullato."""

    DEFAULT_CSS = """
    SudoPasswordModal {
        align: center middle;
    }
    #dialog {
        width: 58;
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
    #error-label {
        color: $error;
        height: auto;
        display: none;
    }
    #error-label.visible {
        display: block;
        margin-bottom: 1;
    }
    #btn-row {
        layout: horizontal;
        height: auto;
        align-horizontal: right;
    }
    #btn-row Button {
        margin-left: 1;
        min-width: 10;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Annulla")]

    def __init__(self, error: str = "") -> None:
        super().__init__()
        self._error = error

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[bold]Password sudo richiesta[/bold]")
            yield Label(
                "ddrescue ha bisogno di privilegi per leggere il dispositivo raw."
            )
            yield Label(self._error, id="error-label",
                        classes="visible" if self._error else "")
            yield Input(placeholder="password", password=True, id="pwd")
            with Vertical(id="btn-row"):
                yield Button("Annulla", id="btn-cancel", variant="default")
                yield Button("Conferma", id="btn-ok", variant="primary")

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
        self.dismiss(self.query_one("#pwd", Input).value)

    def action_cancel(self) -> None:
        self.dismiss("")
