"""Configurazione logging per Minerva."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from minerva.config.settings import LoggingConfig

logger = logging.getLogger(__name__)


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Configura il logging dell'applicazione."""
    if config is None:
        config = LoggingConfig()

    level = getattr(logging, config.level.upper(), logging.INFO)

    # Formato log
    fmt = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler (con rotazione)
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.max_size_mb * 1024 * 1024,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Riduci verbosità di librerie esterne
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def cleanup_old_logs(config: LoggingConfig | None = None) -> int:
    """Rimuove le righe di log più vecchie di retention_hours.

    Legge il file di log, filtra le righe con timestamp più vecchio
    della soglia, e riscrive il file con solo le righe recenti.

    Args:
        config: Configurazione logging. Se None, usa i default.

    Returns:
        Numero di righe rimosse.
    """
    if config is None:
        config = LoggingConfig()

    if config.retention_hours <= 0:
        return 0

    log_path = Path(config.file)
    if not log_path.exists():
        return 0

    cutoff = datetime.now() - timedelta(hours=config.retention_hours)

    try:
        lines = log_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Impossibile leggere il file di log per cleanup: %s", e)
        return 0

    kept: list[str] = []
    removed = 0

    for line in lines:
        # Formato timestamp: "2026-02-10 14:30:45 [..."
        # Prova a parsare i primi 19 caratteri come timestamp
        ts_str = line[:19]
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            if ts < cutoff:
                removed += 1
                continue
        except ValueError:
            # Riga di continuazione (traceback, multilinea): segue il destino
            # dell'ultima riga con timestamp. Se non ci sono righe kept,
            # significa che siamo ancora nella zona vecchia -> scarta.
            if not kept:
                removed += 1
                continue
        kept.append(line)

    if removed > 0:
        try:
            log_path.write_text("".join(kept), encoding="utf-8")
            logger.info(
                "Cleanup log: rimosse %d righe più vecchie di %d ore",
                removed, config.retention_hours,
            )
        except OSError as e:
            logger.warning("Impossibile scrivere il file di log dopo cleanup: %s", e)

    return removed
