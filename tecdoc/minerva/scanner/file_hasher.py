"""Calcolo hash SHA-256 per i file."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BUFFER_SIZE = 65536  # 64KB


def compute_hash(file_path: Path, algorithm: str = "sha256") -> str | None:
    """Calcola l'hash di un file. Restituisce None se il file non è leggibile."""
    try:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            while True:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()
    except (OSError, PermissionError) as e:
        logger.warning("Impossibile calcolare hash per %s: %s", file_path, e)
        return None
