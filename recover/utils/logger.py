"""Logger su file + callback per la TUI."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

_tui_callback: Callable[[str], None] | None = None


def setup(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{ts}.log"

    logger = logging.getLogger("recover")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    tui_handler = _TuiHandler()
    tui_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(tui_handler)

    return logger


def set_tui_callback(cb: Callable[[str], None]) -> None:
    global _tui_callback
    _tui_callback = cb


class _TuiHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if _tui_callback:
            _tui_callback(self.format(record))


def get() -> logging.Logger:
    return logging.getLogger("recover")
