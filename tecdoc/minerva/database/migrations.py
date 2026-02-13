"""Inizializzazione e migrazione dello schema database SQLite."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from minerva.database.models import FTS_SCHEMA_SQL, SCHEMA_SQL, SEED_DATA

logger = logging.getLogger(__name__)


def backup_database(db_path: str, backup_dir: str) -> str | None:
    """Crea una copia di backup del database prima della scansione."""
    db_file = Path(db_path)
    if not db_file.exists():
        return None

    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"minerva_backup_{timestamp}.db"

    shutil.copy2(db_file, backup_file)
    logger.info("Backup database creato: %s", backup_file)
    return str(backup_file)


def init_database(db_path: str) -> sqlite3.Connection:
    """Inizializza il database: crea schema e inserisce dati iniziali."""
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    # Crea lo schema
    conn.executescript(SCHEMA_SQL)

    # Migrazione: aggiunge colonne mancanti a tabelle esistenti
    _ensure_columns(conn)

    # Crea/ricrea tabella FTS5 (separata perché virtual table)
    _ensure_fts_table(conn)
    logger.info("Schema database creato/verificato")

    # Seed dati iniziali (solo se tabelle vuote)
    _seed_if_empty(conn)
    conn.commit()

    logger.info("Database inizializzato: %s", db_path)
    return conn


def get_connection(db_path: str) -> sqlite3.Connection:
    """Restituisce una connessione al database esistente."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Aggiunge colonne mancanti alla tabella documenti (migrazioni incrementali)."""
    cursor = conn.execute("PRAGMA table_info(documenti)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("indice_contenuti", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            conn.execute(f"ALTER TABLE documenti ADD COLUMN {col_name} {col_type}")
            logger.info("Migrazione: aggiunta colonna documenti.%s", col_name)


def _ensure_fts_table(conn: sqlite3.Connection) -> None:
    """Verifica che la tabella FTS5 esista con lo schema corretto.

    Ricrea la tabella se: content-less (vecchio schema) o colonne mancanti.
    """
    cursor = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='documenti_fts'"
    )
    row = cursor.fetchone()

    if row is None:
        # Tabella non esiste: creala
        conn.execute(FTS_SCHEMA_SQL)
        return

    existing_sql = row[0] or ""

    needs_rebuild = False
    # Se contiene 'content=' e' content-less (vecchio schema)
    if "content=" in existing_sql:
        logger.info("Migrazione FTS5: ricreazione tabella da content-less a regular")
        needs_rebuild = True
    # Se manca una colonna prevista (es. indice_contenuti)
    elif "indice_contenuti" not in existing_sql:
        logger.info("Migrazione FTS5: ricreazione tabella per aggiunta colonna indice_contenuti")
        needs_rebuild = True

    if needs_rebuild:
        conn.execute("DROP TABLE documenti_fts")
        conn.execute(FTS_SCHEMA_SQL)


def sync_aree_from_config(conn: sqlite3.Connection, aree: list[tuple[str, str]]) -> None:
    """Sincronizza le aree di classificazione dal config al DB.

    Inserisce le aree mancanti, aggiorna le descrizioni di quelle esistenti.
    Non rimuove aree presenti nel DB ma assenti nel config.

    Args:
        aree: Lista di tuple (codice, descrizione).
    """
    if not aree:
        return

    cursor = conn.cursor()
    inserted = 0
    updated = 0

    for codice, descrizione in aree:
        cursor.execute("SELECT descrizione FROM area WHERE cod_area = ?", (codice,))
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO area (cod_area, descrizione, utente_inserimento) VALUES (?, ?, 'CONFIG')",
                (codice, descrizione),
            )
            inserted += 1
        elif row[0] != descrizione:
            cursor.execute(
                "UPDATE area SET descrizione = ?, utente_modifica = 'CONFIG', "
                "data_modifica = datetime('now','localtime') WHERE cod_area = ?",
                (descrizione, codice),
            )
            updated += 1

    if inserted or updated:
        logger.info("Sync aree da config: %d inserite, %d aggiornate", inserted, updated)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Inserisce i dati iniziali solo se le tabelle sono vuote."""
    cursor = conn.cursor()

    # Stato documento
    cursor.execute("SELECT COUNT(*) FROM stato_documento")
    if cursor.fetchone()[0] == 0:
        for codice, desc in SEED_DATA["stato_documento"]:
            cursor.execute(
                "INSERT INTO stato_documento (stato_codice, stato_descrizione) VALUES (?, ?)",
                (codice, desc),
            )
        logger.info("Seed: stato_documento (%d righe)", len(SEED_DATA["stato_documento"]))

    # Aree
    cursor.execute("SELECT COUNT(*) FROM area")
    if cursor.fetchone()[0] == 0:
        for cod, desc in SEED_DATA["area"]:
            cursor.execute(
                "INSERT INTO area (cod_area, descrizione, utente_inserimento) VALUES (?, ?, 'SYSTEM')",
                (cod, desc),
            )
        logger.info("Seed: area (%d righe)", len(SEED_DATA["area"]))

    # Sotto-aree MES
    cursor.execute("SELECT COUNT(*) FROM sotto_area")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id_area FROM area WHERE cod_area = 'MES'")
        row = cursor.fetchone()
        if row:
            id_area_mes = row[0]
            for cod, desc in SEED_DATA["sotto_area_mes"]:
                cursor.execute(
                    "INSERT INTO sotto_area (cod_sotto_area, id_area, descrizione, utente_inserimento) "
                    "VALUES (?, ?, ?, 'SYSTEM')",
                    (cod, id_area_mes, desc),
                )
            logger.info("Seed: sotto_area MES (%d righe)", len(SEED_DATA["sotto_area_mes"]))

    # Sub-aree APS (sotto sotto_area dell'APS - ma APS non ha sotto-aree nel seed,
    # quindi le sub_area_aps sono sotto-aree dell'APS direttamente)
    # Per ora le inseriamo come sotto_area dell'APS
    cursor.execute("SELECT id_area FROM area WHERE cod_area = 'APS'")
    row = cursor.fetchone()
    if row:
        id_area_aps = row[0]
        cursor.execute(
            "SELECT COUNT(*) FROM sotto_area WHERE id_area = ?", (id_area_aps,)
        )
        if cursor.fetchone()[0] == 0:
            for cod, desc in SEED_DATA["sub_area_aps"]:
                cursor.execute(
                    "INSERT INTO sotto_area (cod_sotto_area, id_area, descrizione, utente_inserimento) "
                    "VALUES (?, ?, ?, 'SYSTEM')",
                    (cod, id_area_aps, desc),
                )
            logger.info("Seed: sotto_area APS (%d righe)", len(SEED_DATA["sub_area_aps"]))

    # Sub-aree Qualità (sotto la sotto_area QUAL del MES)
    cursor.execute(
        "SELECT sa.id_sotto_area FROM sotto_area sa "
        "JOIN area a ON sa.id_area = a.id_area "
        "WHERE a.cod_area = 'MES' AND sa.cod_sotto_area = 'QUAL'"
    )
    row = cursor.fetchone()
    if row:
        id_sotto_area_qual = row[0]
        cursor.execute(
            "SELECT COUNT(*) FROM sub_area WHERE id_sotto_area = ?",
            (id_sotto_area_qual,),
        )
        if cursor.fetchone()[0] == 0:
            for cod, desc in SEED_DATA["sub_area_qual"]:
                cursor.execute(
                    "INSERT INTO sub_area (cod_sub_area, id_sotto_area, descrizione, utente_inserimento) "
                    "VALUES (?, ?, ?, 'SYSTEM')",
                    (cod, id_sotto_area_qual, desc),
                )
            logger.info("Seed: sub_area QUAL (%d righe)", len(SEED_DATA["sub_area_qual"]))

    # Settori
    cursor.execute("SELECT COUNT(*) FROM settore")
    if cursor.fetchone()[0] == 0:
        for cod, desc in SEED_DATA["settore"]:
            cursor.execute(
                "INSERT INTO settore (cod_settore, descrizione, utente_inserimento) VALUES (?, ?, 'SYSTEM')",
                (cod, desc),
            )
        logger.info("Seed: settore (%d righe)", len(SEED_DATA["settore"]))

    # Tipi documento
    cursor.execute("SELECT COUNT(*) FROM tipo_documento")
    if cursor.fetchone()[0] == 0:
        for cod, desc in SEED_DATA["tipo_documento"]:
            cursor.execute(
                "INSERT INTO tipo_documento (cod_tipo_documento, descrizione, utente_inserimento) "
                "VALUES (?, ?, 'SYSTEM')",
                (cod, desc),
            )
        logger.info("Seed: tipo_documento (%d righe)", len(SEED_DATA["tipo_documento"]))

    # FIP
    cursor.execute("SELECT COUNT(*) FROM fip")
    if cursor.fetchone()[0] == 0:
        for cod, desc in SEED_DATA["fip"]:
            cursor.execute(
                "INSERT INTO fip (cod_fip, descrizione) VALUES (?, ?)",
                (cod, desc),
            )
        logger.info("Seed: fip (%d righe)", len(SEED_DATA["fip"]))
