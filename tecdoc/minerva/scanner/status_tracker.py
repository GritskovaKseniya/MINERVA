"""Determinazione dello stato dei documenti (NEW, ESU, MOD, CAN, SPO, DUP, EXD)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def determine_status_existing(
    record_db: dict[str, Any],
    file_exists: bool,
    current_hash: str | None,
    all_current_hashes: dict[str, str],
    all_current_names: dict[str, str],
) -> str:
    """Determina lo stato di un documento già presente nel DB.

    Args:
        record_db: Record esistente nel database.
        file_exists: True se il file esiste ancora al percorso originale.
        current_hash: Hash attuale del file (None se il file non esiste).
        all_current_hashes: Mappa percorso_relativo -> hash di tutti i file trovati.
        all_current_names: Mappa percorso_relativo -> nome_file di tutti i file trovati.

    Returns:
        Codice stato: ESU, MOD, CAN, SPO, DUP, EXD.
    """
    if not file_exists:
        # Il file non è più al percorso originale
        old_hash = record_db.get("documento_hash")
        if old_hash:
            # Cerchiamo lo stesso hash in altri percorsi
            for pr, h in all_current_hashes.items():
                if h == old_hash and pr != record_db["percorso_relativo"]:
                    return "SPO"  # Spostato
        return "CAN"  # Cancellato

    # Il file esiste ancora
    old_hash = record_db.get("documento_hash")
    if current_hash and old_hash and current_hash != old_hash:
        return "MOD"  # Modificato

    # Hash uguale, controlliamo duplicati
    if current_hash:
        nome_file = record_db.get("documento_nome_file", "")
        duplicati = [
            pr for pr, h in all_current_hashes.items()
            if h == current_hash
            and pr != record_db["percorso_relativo"]
            and all_current_names.get(pr, "") == nome_file
        ]
        if duplicati:
            return "EXD"  # Esistente con Duplicati

    return "ESU"  # Esistente Unico


def determine_status_new(
    file_hash: str | None,
    nome_file: str,
    existing_records: list[dict[str, Any]],
) -> str:
    """Determina lo stato di un file nuovo (non presente nel DB).

    Args:
        file_hash: Hash del nuovo file.
        nome_file: Nome del file.
        existing_records: Record esistenti nel DB con lo stesso hash e nome.

    Returns:
        Codice stato: NEW o DUP.
    """
    if file_hash and existing_records:
        # Stesso hash e nome file già presenti -> è un duplicato
        matching = [
            r for r in existing_records
            if r.get("documento_hash") == file_hash
            and r.get("documento_nome_file") == nome_file
        ]
        if matching:
            return "DUP"

    return "NEW"
