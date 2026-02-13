"""Entry point per l'interfaccia web Minerva."""

from __future__ import annotations

import argparse
import sys

from minerva.config.settings import load_config
from minerva.utils.logging_config import setup_logging
from minerva.web.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minerva Web - Interfaccia di ricerca e classificazione documenti"
    )
    parser.add_argument(
        "-c", "--config",
        default="minerva_config.json",
        help="Percorso file di configurazione (default: minerva_config.json)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Attiva la modalita' debug di Flask",
    )

    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.logging)

    if args.debug:
        config.web.debug = True

    app = create_app(config)
    app.run(
        host=config.web.host,
        port=config.web.port,
        debug=config.web.debug,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
