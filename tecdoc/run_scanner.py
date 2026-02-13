"""Entry point per lo scanner Minerva."""

from __future__ import annotations

import argparse
import sys

from minerva.config.settings import load_config
from minerva.scanner.orchestrator import run_scan
from minerva.utils.logging_config import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minerva Scanner - Censimento e classificazione documenti"
    )
    parser.add_argument(
        "-c", "--config",
        default="minerva_config.json",
        help="Percorso file di configurazione (default: minerva_config.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Esegue la scansione senza modificare il database",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Scansione rigenerativa: cancella tutti i documenti e riscansiona da zero",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Scansiona solo un file specifico o una sottocartella "
             "(es. --path 'ClienteX/progetto/doc.docx' oppure --path 'ClienteX/progetto')",
    )

    args = parser.parse_args()

    # Carica config e setup logging
    config = load_config(args.config)
    setup_logging(config.logging)

    # Esegui scansione
    stats = run_scan(
        config=config,
        dry_run=args.dry_run,
        regenerate=args.regenerate,
        filter_path=args.path,
    )

    if stats.errori:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
