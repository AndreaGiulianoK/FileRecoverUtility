"""Widget riutilizzabile per la selezione modalità di recupero."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static

MODES = {
    "A": {
        "label": "A — Recupero file cancellati",
        "tool": "testdisk",
        "when": "Il filesystem è ancora leggibile (card formattata accidentalmente, file eliminati)",
        "how": "Legge la struttura del filesystem per trovare i file cancellati. "
               "I file vengono recuperati con il nome originale.",
        "pro": "Nomi originali, struttura cartelle, selezione selettiva dei file",
        "con": "Non funziona se il filesystem è corrotto o la card è fisicamente danneggiata",
        "variant": "primary",
    },
    "B": {
        "label": "B — Recupero da filesystem corrotto",
        "tool": "photorec",
        "when": "Il filesystem è corrotto, la card è danneggiata, o la modalità A non ha trovato nulla",
        "how": "Scansiona l'immagine byte per byte cercando le 'firme' dei file (magic bytes). "
               "Non dipende dal filesystem.",
        "pro": "Funziona anche con filesystem completamente distrutto, massimo recupero grezzo",
        "con": "I file perdono il nome originale (es. f0001.jpg). Più lento.",
        "variant": "warning",
    },
    "C": {
        "label": "C — Solo imaging",
        "tool": "ddrescue",
        "when": "Vuoi solo creare una copia sicura .img del dispositivo adesso e decidere dopo",
        "how": "Crea l'immagine disco con ddrescue e si ferma. "
               "Puoi riprendere il recupero in seguito da 'Riprendi sessione'.",
        "pro": "Veloce, non invasivo, preserva lo stato attuale della card",
        "con": "Non recupera nessun file — solo imaging",
        "variant": "default",
    },
}


class ModeSelector(Widget):
    """Mostra le modalità con descrizione e gestisce la selezione."""

    selected: reactive[str | None] = reactive(None)

    DEFAULT_CSS = """
    ModeSelector {
        height: auto;
    }
    .mode-card {
        border: solid $panel;
        margin: 0 0 1 0;
        padding: 0 1;
        height: auto;
    }
    .mode-card.selected {
        border: solid $accent;
        background: $boost;
    }
    .mode-title { text-style: bold; margin-bottom: 0; }
    .mode-when  { color: $text-muted; }
    .mode-how   { margin-top: 1; }
    .mode-pro   { color: $success; }
    .mode-con   { color: $warning; }
    .mode-btn   { margin-top: 1; }
    """

    def __init__(self, include_modes: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._include = include_modes or list(MODES)

    def compose(self) -> ComposeResult:
        for mid in self._include:
            m = MODES[mid]
            with Vertical(id=f"card-{mid}", classes="mode-card"):
                yield Static(m["label"], classes="mode-title")
                yield Static(f"[dim]Quando usarla:[/dim] {m['when']}", classes="mode-when")
                yield Static(f"[dim]Come funziona:[/dim] {m['how']}", classes="mode-how")
                yield Static(f"[green]+[/green] {m['pro']}", classes="mode-pro")
                yield Static(f"[yellow]−[/yellow] {m['con']}", classes="mode-con")
                yield Button(
                    f"Seleziona modalità {mid}",
                    id=f"btn-mode-{mid}",
                    variant=m["variant"],
                    classes="mode-btn",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if not bid.startswith("btn-mode-"):
            return
        event.stop()
        mid = bid.replace("btn-mode-", "")
        self.selected = mid
        # evidenzia la card selezionata
        for m in self._include:
            card = self.query_one(f"#card-{m}")
            if m == mid:
                card.add_class("selected")
            else:
                card.remove_class("selected")
        self.post_message(self.ModeSelected(mid))

    class ModeSelected(Message):
        def __init__(self, mode: str) -> None:
            super().__init__()
            self.mode = mode
