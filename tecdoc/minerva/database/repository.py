"""Operazioni CRUD sul database Minerva."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository per operazioni CRUD sulla tabella documenti."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_percorso_relativo(self, percorso_relativo: str) -> dict[str, Any] | None:
        """Cerca un documento per percorso relativo (chiave univoca)."""
        cursor = self.conn.execute(
            "SELECT * FROM documenti WHERE percorso_relativo = ?",
            (percorso_relativo,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def find_by_hash_and_name(self, doc_hash: str, nome_file: str) -> list[dict[str, Any]]:
        """Cerca documenti con lo stesso hash e nome file."""
        cursor = self.conn.execute(
            "SELECT * FROM documenti WHERE documento_hash = ? AND documento_nome_file = ?",
            (doc_hash, nome_file),
        )
        return [dict(r) for r in cursor.fetchall()]

    def find_by_hash(self, doc_hash: str) -> list[dict[str, Any]]:
        """Cerca documenti con lo stesso hash."""
        cursor = self.conn.execute(
            "SELECT * FROM documenti WHERE documento_hash = ?",
            (doc_hash,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def find_by_cliente(self, cliente_cartella: str) -> list[dict[str, Any]]:
        """Trova tutti i documenti di un cliente."""
        cursor = self.conn.execute(
            "SELECT * FROM documenti WHERE cliente_cartella = ? ORDER BY documento_nome_file",
            (cliente_cartella,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def get_all_for_scan(self) -> list[dict[str, Any]]:
        """Ottiene tutti i documenti per la logica di scansione."""
        cursor = self.conn.execute(
            "SELECT id_documento, percorso_relativo, percorso_base, documento_nome_file, "
            "documento_hash, stato, cliente_cartella FROM documenti"
        )
        return [dict(r) for r in cursor.fetchall()]

    def delete_all_documents(self, cliente_cartella: str | None = None) -> int:
        """Cancella tutti i documenti (e relazioni M2M). Restituisce il conteggio.

        Se cliente_cartella è specificato, cancella solo i documenti di quel cliente.
        """
        if cliente_cartella:
            cursor = self.conn.execute(
                "DELETE FROM documenti WHERE cliente_cartella = ?", (cliente_cartella,)
            )
        else:
            cursor = self.conn.execute("DELETE FROM documenti")
        count = cursor.rowcount
        logger.info("Scansione rigenerativa: rimossi %d documenti%s",
                     count, f" per {cliente_cartella}" if cliente_cartella else "")
        return count

    def insert_document(self, doc: dict[str, Any]) -> int:
        """Inserisce un nuovo documento. Restituisce l'id_documento."""
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        utente = doc.get("inserimento_utente", "MINERVA_SCANNER")

        cursor = self.conn.execute(
            """INSERT INTO documenti (
                cliente_cartella, percorso_base, percorso_relativo,
                documento_nome_file, documento_titolo, documento_revisione,
                documento_revisione_data, documento_data_creazione,
                documento_data_ultima_modifica, documento_dimensione,
                documento_estensione, documento_hash, stato, classificazione,
                attivo, autore, autore_ultima_modifica, versione_interna,
                documento_parole_chiave, fip, titoli_estratti, indice_contenuti,
                sommario_estratto, metadati_json, id_documento_principale,
                inserimento_utente, ultimo_censimento_data, ultimo_censimento_utente
            ) VALUES (
                :cliente_cartella, :percorso_base, :percorso_relativo,
                :documento_nome_file, :documento_titolo, :documento_revisione,
                :documento_revisione_data, :documento_data_creazione,
                :documento_data_ultima_modifica, :documento_dimensione,
                :documento_estensione, :documento_hash, :stato, 'Non Classificato',
                0, :autore, :autore_ultima_modifica, :versione_interna,
                :documento_parole_chiave, :fip, :titoli_estratti, :indice_contenuti,
                :sommario_estratto, :metadati_json, :id_documento_principale,
                :inserimento_utente, :ultimo_censimento_data, :ultimo_censimento_utente
            )""",
            {
                "cliente_cartella": doc["cliente_cartella"],
                "percorso_base": doc["percorso_base"],
                "percorso_relativo": doc["percorso_relativo"],
                "documento_nome_file": doc["documento_nome_file"],
                "documento_titolo": doc.get("documento_titolo"),
                "documento_revisione": doc.get("documento_revisione"),
                "documento_revisione_data": doc.get("documento_revisione_data"),
                "documento_data_creazione": doc.get("documento_data_creazione"),
                "documento_data_ultima_modifica": doc.get("documento_data_ultima_modifica"),
                "documento_dimensione": doc.get("documento_dimensione"),
                "documento_estensione": doc.get("documento_estensione"),
                "documento_hash": doc.get("documento_hash"),
                "stato": doc.get("stato", "NEW"),
                "autore": doc.get("autore"),
                "autore_ultima_modifica": doc.get("autore_ultima_modifica"),
                "versione_interna": doc.get("versione_interna"),
                "documento_parole_chiave": doc.get("documento_parole_chiave"),
                "fip": doc.get("fip"),
                "titoli_estratti": doc.get("titoli_estratti"),
                "indice_contenuti": doc.get("indice_contenuti"),
                "sommario_estratto": doc.get("sommario_estratto"),
                "metadati_json": doc.get("metadati_json"),
                "id_documento_principale": doc.get("id_documento_principale"),
                "inserimento_utente": utente,
                "ultimo_censimento_data": now,
                "ultimo_censimento_utente": utente,
            },
        )
        return cursor.lastrowid  # type: ignore[return-value]

    def update_scan_fields(self, percorso_relativo: str, updates: dict[str, Any]) -> None:
        """Aggiorna i campi dello scanner. NON sovrascrive i campi già compilati manualmente."""
        existing = self.find_by_percorso_relativo(percorso_relativo)
        if not existing:
            return

        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        utente = updates.get("ultimo_censimento_utente", "MINERVA_SCANNER")

        # Campi che lo scanner aggiorna SEMPRE
        always_update = {
            "documento_hash": updates.get("documento_hash"),
            "documento_data_ultima_modifica": updates.get("documento_data_ultima_modifica"),
            "documento_dimensione": updates.get("documento_dimensione"),
            "stato": updates.get("stato"),
            "ultimo_censimento_data": now,
            "ultimo_censimento_utente": utente,
            "ultima_modifica_data": now,
            "ultima_modifica_utente": utente,
        }

        # Campi che lo scanner aggiorna SOLO se il valore nel DB è NULL/vuoto
        fill_if_empty = [
            "documento_titolo", "autore", "autore_ultima_modifica",
            "versione_interna", "documento_parole_chiave", "fip",
            "titoli_estratti", "indice_contenuti", "sommario_estratto",
            "documento_revisione",
        ]

        set_clauses = []
        params: list[Any] = []

        for col, val in always_update.items():
            if val is not None:
                set_clauses.append(f"{col} = ?")
                params.append(val)

        for col in fill_if_empty:
            new_val = updates.get(col)
            if new_val is not None and not existing.get(col):
                set_clauses.append(f"{col} = ?")
                params.append(new_val)

        if not set_clauses:
            return

        sql = f"UPDATE documenti SET {', '.join(set_clauses)} WHERE percorso_relativo = ?"
        params.append(percorso_relativo)
        self.conn.execute(sql, params)

    def update_stato(self, percorso_relativo: str, nuovo_stato: str) -> None:
        """Aggiorna solo lo stato di un documento."""
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.conn.execute(
            "UPDATE documenti SET stato = ?, ultima_modifica_data = ? WHERE percorso_relativo = ?",
            (nuovo_stato, now, percorso_relativo),
        )

    def update_documento_principale(self, id_documento: int, id_principale: int | None) -> None:
        """Aggiorna il riferimento al documento principale (per revisioni)."""
        self.conn.execute(
            "UPDATE documenti SET id_documento_principale = ? WHERE id_documento = ?",
            (id_principale, id_documento),
        )

    def update_classification(self, id_documento: int, updates: dict[str, Any]) -> None:
        """Aggiorna i campi di classificazione manuale (da interfaccia web)."""
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        utente = updates.get("ultima_modifica_utente", "WEB_USER")

        set_clauses = ["ultima_modifica_data = ?", "ultima_modifica_utente = ?"]
        params: list[Any] = [now, utente]

        allowed_fields = [
            "classificazione", "attivo", "descrizione", "progetto",
            "documento_parole_chiave", "documento_titolo",
        ]
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = ?")
                params.append(updates[field])

        sql = f"UPDATE documenti SET {', '.join(set_clauses)} WHERE id_documento = ?"
        params.append(id_documento)
        self.conn.execute(sql, params)

    def set_auto_classifications(
        self,
        id_documento: int,
        area_codes: list[str],
        area_id_map: dict[str, int],
    ) -> int:
        """Inserisce le classificazioni area auto-rilevate nella tabella M2M.

        NON sovrascrive classificazioni esistenti: opera solo se il documento
        non ha ancora classificazioni nella tabella documento_classificazione.

        Args:
            id_documento: ID del documento.
            area_codes: Lista di codici area rilevati (es. ["MES", "APS"]).
            area_id_map: Mappa cod_area -> id_area.

        Returns:
            Numero di classificazioni inserite.
        """
        if not area_codes:
            return 0

        # Controlla se il documento ha già classificazioni manuali
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM documento_classificazione WHERE id_documento = ?",
            (id_documento,),
        )
        if cursor.fetchone()[0] > 0:
            return 0

        inserted = 0
        for code in area_codes:
            id_area = area_id_map.get(code)
            if id_area is None:
                continue
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO documento_classificazione "
                    "(id_documento, id_area) VALUES (?, ?)",
                    (id_documento, id_area),
                )
                inserted += 1
            except Exception:
                pass

        # Aggiorna il campo classificazione del documento in base alle aree inserite
        if inserted > 0:
            self.conn.execute(
                "UPDATE documenti SET classificazione = 'Parzialmente Classificato' "
                "WHERE id_documento = ? AND classificazione = 'Non Classificato'",
                (id_documento,),
            )

        return inserted

    def get_all_percorsi_relativi(self) -> set[str]:
        """Restituisce tutti i percorsi relativi presenti nel DB."""
        cursor = self.conn.execute("SELECT percorso_relativo FROM documenti")
        return {row[0] for row in cursor.fetchall()}

    def mark_not_found_as_deleted(
        self, found_percorsi: set[str], all_file_hashes: dict[str, str]
    ) -> tuple[int, int]:
        """Segna come CAN o SPO i documenti non trovati nella scansione corrente.

        Restituisce (count_cancellati, count_spostati).
        """
        all_db = self.get_all_for_scan()
        cancellati = 0
        spostati = 0

        for record in all_db:
            pr = record["percorso_relativo"]
            if pr in found_percorsi:
                continue
            if record["stato"] == "CAN":
                continue

            old_hash = record["documento_hash"]
            # Controlla se lo stesso hash esiste in un percorso diverso tra quelli trovati
            if old_hash and old_hash in all_file_hashes.values():
                self.update_stato(pr, "SPO")
                spostati += 1
            else:
                self.update_stato(pr, "CAN")
                cancellati += 1

        return cancellati, spostati

    def get_revision_counts(self) -> dict[int, int]:
        """Restituisce il conteggio delle revisioni per ogni documento principale."""
        cursor = self.conn.execute(
            "SELECT id_documento_principale, COUNT(*) as cnt "
            "FROM documenti WHERE id_documento_principale IS NOT NULL "
            "GROUP BY id_documento_principale"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}

    def get_revisions_for_document(self, doc_id: int) -> list[dict[str, Any]]:
        """Restituisce le revisioni precedenti di un documento (escluso se stesso)."""
        cursor = self.conn.execute(
            "SELECT id_documento, documento_nome_file, documento_revisione, "
            "documento_data_creazione, stato "
            "FROM documenti WHERE id_documento_principale = ? AND id_documento != ? "
            "ORDER BY documento_data_creazione DESC",
            (doc_id, doc_id),
        )
        return [dict(r) for r in cursor.fetchall()]

    def search_documents(
        self,
        cliente: str | None = None,
        titolo: str | None = None,
        contenuto: str | None = None,
        stato: str | None = None,
        classificazione: str | None = None,
        attivo: int | None = None,
        id_area: int | None = None,
        id_settore: int | None = None,
        only_principal: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Ricerca documenti con filtri. Restituisce (risultati, conteggio_totale).

        Args:
            titolo: Ricerca nel nome file e titolo documento (con wildcards).
            contenuto: Ricerca in parole chiave, descrizione e sommario.
            only_principal: Se True, esclude le revisioni secondarie.
        """
        where_clauses = []
        params: list[Any] = []

        # Escludi revisioni secondarie: mostra solo documenti che NON puntano a un principale
        if only_principal:
            where_clauses.append("d.id_documento_principale IS NULL")

        if cliente:
            where_clauses.append("d.cliente_cartella = ?")
            params.append(cliente)
        if titolo:
            where_clauses.append(
                "(d.documento_nome_file LIKE ? OR d.documento_titolo LIKE ?)"
            )
            like_titolo = f"%{titolo}%"
            params.extend([like_titolo, like_titolo])
        if contenuto:
            where_clauses.append(
                "(d.documento_parole_chiave LIKE ? OR d.descrizione LIKE ? "
                "OR d.sommario_estratto LIKE ?)"
            )
            like_cont = f"%{contenuto}%"
            params.extend([like_cont, like_cont, like_cont])
        if stato:
            where_clauses.append("d.stato = ?")
            params.append(stato)
        if classificazione:
            where_clauses.append("d.classificazione = ?")
            params.append(classificazione)
        if attivo is not None:
            where_clauses.append("d.attivo = ?")
            params.append(attivo)
        if id_settore:
            where_clauses.append("c.id_settore = ?")
            params.append(id_settore)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        join_area = ""
        if id_area:
            join_area = "JOIN documento_classificazione dc ON d.id_documento = dc.id_documento"
            if where_sql:
                where_sql += " AND dc.id_area = ?"
            else:
                where_sql = "WHERE dc.id_area = ?"
            params.append(id_area)

        base_sql = (
            f"FROM documenti d "
            f"LEFT JOIN cliente c ON d.cliente_cartella = c.cliente_cartella "
            f"{join_area} "
            f"{where_sql}"
        )

        # Count
        count_params = list(params)
        cursor = self.conn.execute(f"SELECT COUNT(DISTINCT d.id_documento) {base_sql}", count_params)
        total = cursor.fetchone()[0]

        # Risultati
        params.extend([limit, offset])
        cursor = self.conn.execute(
            f"SELECT DISTINCT d.* {base_sql} ORDER BY d.documento_nome_file LIMIT ? OFFSET ?",
            params,
        )
        results = [dict(r) for r in cursor.fetchall()]

        return results, total

    def get_clienti(self) -> list[str]:
        """Restituisce la lista di tutti i clienti (cartelle) censiti."""
        cursor = self.conn.execute(
            "SELECT DISTINCT cliente_cartella FROM documenti ORDER BY cliente_cartella"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_directories_for_cliente(self, cliente: str) -> list[str]:
        """Restituisce le directory distinte per un cliente."""
        cursor = self.conn.execute(
            "SELECT DISTINCT percorso_relativo FROM documenti WHERE cliente_cartella = ?",
            (cliente,),
        )
        dirs = set()
        for row in cursor.fetchall():
            parts = row[0].replace("\\", "/").split("/")
            # Costruisci i percorsi delle directory intermedie
            for i in range(1, len(parts)):
                dirs.add("/".join(parts[:i]))
        return sorted(dirs)

    # --- Full-Text Search ---

    def fts_index_document(self, id_documento: int, fields: dict[str, Any]) -> None:
        """Inserisce o aggiorna un documento nell'indice full-text."""
        # Rimuovi eventuale voce esistente
        self.conn.execute(
            "DELETE FROM documenti_fts WHERE rowid = ?", (id_documento,)
        )
        # Inserisci nuova voce
        self.conn.execute(
            "INSERT INTO documenti_fts(rowid, "
            "documento_nome_file, documento_titolo, testo_contenuto, "
            "documento_parole_chiave, titoli_estratti, indice_contenuti, sommario_estratto) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                id_documento,
                fields.get("documento_nome_file", ""),
                fields.get("documento_titolo", ""),
                fields.get("testo_contenuto", ""),
                fields.get("documento_parole_chiave", ""),
                fields.get("titoli_estratti", ""),
                fields.get("indice_contenuti", ""),
                fields.get("sommario_estratto", ""),
            ),
        )

    def fts_delete_document(self, id_documento: int) -> None:
        """Rimuove un documento dall'indice full-text."""
        self.conn.execute(
            "DELETE FROM documenti_fts WHERE rowid = ?", (id_documento,)
        )

    def fts_delete_all(self) -> None:
        """Svuota completamente l'indice full-text."""
        self.conn.execute("DELETE FROM documenti_fts")

    def fts_search(
        self,
        query: str,
        cliente: str | None = None,
        only_principal: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Ricerca full-text nei documenti. Restituisce (risultati con snippet, totale).

        Args:
            only_principal: Se True (default), cerca solo nei documenti di ultima revisione.
        """
        # Sanitizza la query per FTS5
        fts_query = _sanitize_fts_query(query)
        if not fts_query:
            return [], 0

        extra_where = ""
        params_extra: list[Any] = []
        if cliente:
            extra_where += "AND d.cliente_cartella = ? "
            params_extra.append(cliente)
        if only_principal:
            extra_where += "AND d.id_documento_principale IS NULL "

        # Count
        count_sql = (
            f"SELECT COUNT(*) FROM documenti_fts f "
            f"JOIN documenti d ON f.rowid = d.id_documento "
            f"WHERE f.documenti_fts MATCH ? {extra_where}"
        )
        cursor = self.conn.execute(count_sql, [fts_query] + params_extra)
        total = cursor.fetchone()[0]

        # Risultati con snippet e ranking BM25
        search_sql = (
            f"SELECT d.*, "
            f"snippet(documenti_fts, 2, '<mark>', '</mark>', '...', 40) as snippet_testo, "
            f"snippet(documenti_fts, 1, '<mark>', '</mark>', '...', 20) as snippet_titolo, "
            f"rank "
            f"FROM documenti_fts f "
            f"JOIN documenti d ON f.rowid = d.id_documento "
            f"WHERE f.documenti_fts MATCH ? {extra_where} "
            f"ORDER BY rank "
            f"LIMIT ? OFFSET ?"
        )
        cursor = self.conn.execute(
            search_sql, [fts_query] + params_extra + [limit, offset]
        )
        results = [dict(r) for r in cursor.fetchall()]

        return results, total


def _sanitize_fts_query(query: str) -> str:
    """Converte la query utente in formato FTS5 sicuro."""
    # Rimuovi caratteri speciali FTS5 che potrebbero causare errori
    cleaned = query.strip()
    if not cleaned:
        return ""

    # Se contiene operatori FTS5 espliciti (AND, OR, NOT, NEAR), lascia passare
    has_operators = any(
        f" {op} " in cleaned.upper()
        for op in ["AND", "OR", "NOT", "NEAR"]
    )
    if has_operators:
        return cleaned

    # Altrimenti, tratta come ricerca per termini: ogni parola con prefisso *
    words = cleaned.split()
    terms = []
    for w in words:
        # Rimuovi caratteri speciali
        w = w.strip('"\'(){}[]^~')
        if w:
            terms.append(f'"{w}"')
    return " AND ".join(terms) if terms else ""


class ClienteRepository:
    """Repository per operazioni CRUD sulla tabella cliente."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ensure_cliente(self, cliente_cartella: str, utente: str = "MINERVA_SCANNER") -> None:
        """Inserisce il cliente se non esiste già."""
        cursor = self.conn.execute(
            "SELECT 1 FROM cliente WHERE cliente_cartella = ?",
            (cliente_cartella,),
        )
        if cursor.fetchone() is None:
            self.conn.execute(
                "INSERT INTO cliente (cliente_cartella, utente_inserimento) VALUES (?, ?)",
                (cliente_cartella, utente),
            )
            logger.info("Nuovo cliente censito: %s", cliente_cartella)

    def get_all(self) -> list[dict[str, Any]]:
        """Restituisce tutti i clienti con info settore."""
        cursor = self.conn.execute(
            "SELECT c.*, s.cod_settore, s.descrizione as settore_descrizione "
            "FROM cliente c LEFT JOIN settore s ON c.id_settore = s.id_settore "
            "ORDER BY c.cliente_cartella"
        )
        return [dict(r) for r in cursor.fetchall()]

    def update_settore(self, cliente_cartella: str, id_settore: int, utente: str = "WEB_USER") -> None:
        """Aggiorna il settore di un cliente."""
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        self.conn.execute(
            "UPDATE cliente SET id_settore = ?, data_modifica = ?, utente_modifica = ? "
            "WHERE cliente_cartella = ?",
            (id_settore, now, utente, cliente_cartella),
        )


class LookupRepository:
    """Repository per le tabelle di lookup (area, sotto_area, settore, tipo_documento, fip)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_aree(self) -> list[dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM area WHERE abilitato = 1 ORDER BY cod_area")
        return [dict(r) for r in cursor.fetchall()]

    def get_sotto_aree(self, id_area: int | None = None) -> list[dict[str, Any]]:
        if id_area:
            cursor = self.conn.execute(
                "SELECT * FROM sotto_area WHERE abilitato = 1 AND id_area = ? ORDER BY cod_sotto_area",
                (id_area,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM sotto_area WHERE abilitato = 1 ORDER BY id_area, cod_sotto_area"
            )
        return [dict(r) for r in cursor.fetchall()]

    def get_sub_aree(self, id_sotto_area: int | None = None) -> list[dict[str, Any]]:
        if id_sotto_area:
            cursor = self.conn.execute(
                "SELECT * FROM sub_area WHERE abilitato = 1 AND id_sotto_area = ? ORDER BY cod_sub_area",
                (id_sotto_area,),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM sub_area WHERE abilitato = 1 ORDER BY id_sotto_area, cod_sub_area"
            )
        return [dict(r) for r in cursor.fetchall()]

    def get_settori(self) -> list[dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM settore WHERE abilitato = 1 ORDER BY cod_settore")
        return [dict(r) for r in cursor.fetchall()]

    def get_tipi_documento(self) -> list[dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM tipo_documento WHERE abilitato = 1 ORDER BY cod_tipo_documento"
        )
        return [dict(r) for r in cursor.fetchall()]

    def get_fip(self) -> list[dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM fip WHERE abilitato = 1 ORDER BY cod_fip")
        return [dict(r) for r in cursor.fetchall()]

    def get_stati_documento(self) -> list[dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM stato_documento ORDER BY stato_codice")
        return [dict(r) for r in cursor.fetchall()]

    def get_area_id_map(self) -> dict[str, int]:
        """Restituisce una mappa cod_area -> id_area per tutte le aree abilitate."""
        cursor = self.conn.execute(
            "SELECT cod_area, id_area FROM area WHERE abilitato = 1"
        )
        return {row[0]: row[1] for row in cursor.fetchall()}
