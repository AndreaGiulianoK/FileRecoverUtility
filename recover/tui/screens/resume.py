"""Schermata ripresa da immagine .img esistente."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from recover.core.session import Session
from recover.tui.widgets.mode_selector import ModeSelector
from recover.utils.fs import BlockDevice


def _find_images(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        return []
    return sorted(image_dir.glob("*.img"), key=lambda p: p.stat().st_mtime, reverse=True)


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"


class ResumeScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Indietro")]

    def __init__(self, app_cfg: dict[str, Any]) -> None:
        super().__init__()
        self._cfg = app_cfg
        self._selected_path: Path | None = None
        self._mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Riprendi da immagine esistente", classes="screen-title")
        yield Static("1. Seleziona immagine  (più recenti prima):", id="list-label")
        yield DataTable(id="img-table", cursor_type="row")
        with Vertical(id="manual-box"):
            yield Label("Oppure path manuale:")
            yield Input(placeholder="/percorso/immagine.img", id="manual-input")
        yield Static("", id="selected-label")
        yield Static("2. Scegli la modalità di recupero:", id="mode-label")
        with ScrollableContainer(id="mode-scroll"):
            yield ModeSelector(include_modes=["A", "B"], id="mode-sel")
        yield Static("[dim]Seleziona un'immagine e poi la modalità per procedere.[/dim]", id="hint")
        yield Footer()

    def on_mount(self) -> None:
        from recover.utils import config as cfg_mod
        img_dir = cfg_mod.image_dir(self._cfg)
        images = _find_images(img_dir)

        table: DataTable = self.query_one("#img-table")
        table.add_columns("Nome", "Dimensione", "Data")

        if images:
            for img in images:
                stat = img.stat()
                date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                table.add_row(img.name, _human(stat.st_size), date)
            self._images = images
        else:
            self._images = []
            self.query_one("#list-label", Static).update(
                "[yellow]Nessuna immagine trovata in ~/RECOVER/dsks.[/yellow]\n"
                "Usa il campo manuale per indicare il percorso."
            )

        self._update_mode_buttons()

    def _update_mode_buttons(self) -> None:
        for mid in ("A", "B"):
            btn = self.query_one(f"#mode-{mid}", Button)
            btn.variant = "primary" if mid == self._mode else "default"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self._images and event.cursor_row < len(self._images):
            self._selected_path = self._images[event.cursor_row]
            self._show_selected()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._try_manual(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        p = Path(event.value).expanduser()
        if p.is_file() and p.suffix == ".img":
            self._selected_path = p
            self._show_selected()

    def _try_manual(self, value: str) -> None:
        p = Path(value).expanduser()
        if not p.exists():
            self.query_one("#hint", Static).update(f"[red]File non trovato: {p}[/]")
            return
        if p.suffix != ".img":
            self.query_one("#hint", Static).update("[red]Il file deve avere estensione .img[/]")
            return
        self._selected_path = p
        self._show_selected()

    def _show_selected(self) -> None:
        if not self._selected_path:
            return
        stat = self._selected_path.stat()
        self.query_one("#selected-label", Static).update(
            f"[green]✓ Immagine selezionata:[/] {self._selected_path.name}  ({_human(stat.st_size)})"
        )
        self.query_one("#hint", Static).update(
            "[dim]Ora scegli la modalità qui sotto per avviare il recupero.[/dim]"
        )

    def on_mode_selector_mode_selected(self, event: ModeSelector.ModeSelected) -> None:
        self._mode = event.mode
        if self._selected_path is None:
            self.query_one("#hint", Static).update(
                "[red]Seleziona prima un'immagine dalla lista o dal campo manuale.[/]"
            )
            return
        self._launch()

    def _launch(self) -> None:
        assert self._selected_path is not None
        img = self._selected_path

        # cerca il mapfile corrispondente
        map_path = img.with_suffix(".map")

        # costruisce un BlockDevice fittizio che rappresenta l'immagine
        fake_dev = BlockDevice(
            name=img.stem,
            path=str(img),
            size=_human(img.stat().st_size),
            fstype="",
            label=img.stem,
            mountpoint="",
            removable=False,
        )

        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        session = Session(
            device=fake_dev,
            mode=self._mode,
            timestamp=ts,
            image_path=img,
            map_path=map_path if map_path.exists() else None,
        )

        # crea session_dir nell'output dir
        from recover.utils import config as cfg_mod
        base_out = cfg_mod.output_dir(self._cfg)
        from recover.utils.fs import session_dir as make_session_dir
        session.session_dir = make_session_dir(base_out, fake_dev, ts)
        session.session_dir.mkdir(parents=True, exist_ok=True)

        from recover.tui.screens.verify import VerifyScreen
        self.app.switch_screen(VerifyScreen(session, self._cfg))
