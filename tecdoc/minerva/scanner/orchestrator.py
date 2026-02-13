"""Orchestratore principale della scansione documenti."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from minerva.config.settings import (
    MinervaConfig,
    load_censimento_filtro,
    load_config,
)
from minerva.database.migrations import backup_database, init_database, sync_aree_from_config
from minerva.database.repository import (
    ClienteRepository,
    DocumentRepository,
    LookupRepository,
)
from minerva.scanner.ai_classifier import (
    check_ollama_available,
    classify_document,
)
from minerva.scanner.auto_tagger import (
    auto_tag_from_content,
    auto_tag_from_filename,
    auto_tag_from_path,
    merge_auto_tags,
)
from minerva.scanner.directory_walker import walk_client_directory
from minerva.scanner.file_hasher import compute_hash
from minerva.scanner.metadata_extractor import extract_metadata
from minerva.scanner.revision_detector import group_revisions, is_in_old_folder, parse_revision
from minerva.utils.logging_config import cleanup_old_logs
from minerva.scanner.status_tracker import (
    determine_status_existing,
    determine_status_new,
)

logger = logging.getLogger(__name__)


@dataclass
class ScanStats:
    """Statistiche della scansione."""

    clienti_processati: int = 0
    file_trovati: int = 0
    file_nuovi: int = 0
    file_modificati: int = 0
    file_cancellati: int = 0
    file_spostati: int = 0
    file_duplicati: int = 0
    file_con_errori: int = 0
    revisioni_rilevate: int = 0
    classificazioni_ai: int = 0
    tempo_totale_secondi: float = 0.0
    errori: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Restituisce un riepilogo leggibile."""
        lines = [
            "=" * 60,
            "RIEPILOGO SCANSIONE MINERVA",
            "=" * 60,
            f"Clienti processati:     {self.clienti_processati}",
            f"File trovati:           {self.file_trovati}",
            f"Nuovi (NEW):            {self.file_nuovi}",
            f"Modificati (MOD):       {self.file_modificati}",
            f"Cancellati (CAN):       {self.file_cancellati}",
            f"Spostati (SPO):         {self.file_spostati}",
            f"Duplicati (DUP):        {self.file_duplicati}",
            f"Errori file:            {self.file_con_errori}",
            f"Gruppi revisioni:       {self.revisioni_rilevate}",
            f"Classificazioni AI:     {self.classificazioni_ai}",
            f"Tempo totale:           {self.tempo_totale_secondi:.1f}s",
        ]
        if self.errori:
            lines.append(f"Errori:                 {len(self.errori)}")
            for e in self.errori[:10]:
                lines.append(f"  - {e}")
            if len(self.errori) > 10:
                lines.append(f"  ... e altri {len(self.errori) - 10}")
        lines.append("=" * 60)
        return "\n".join(lines)


def run_scan(
    config: MinervaConfig | None = None,
    config_path: str | None = None,
    dry_run: bool = False,
    regenerate: bool = False,
    filter_path: str | None = None,
) -> ScanStats:
    """Esegue la scansione completa di tutti i percorsi configurati.

    Args:
        config: Configurazione Minerva. Se None, viene caricata dal file.
        config_path: Percorso del file di configurazione.
        dry_run: Se True, non modifica il database.
        regenerate: Se True, cancella tutti i documenti e riscansiona da zero.
        filter_path: Se specificato, scansiona solo questo file/sottocartella
                     (percorso relativo o assoluto).

    Returns:
        Statistiche della scansione.
    """
    start_time = time.time()
    stats = ScanStats()

    # 1. Carica configurazione
    if config is None:
        config = load_config(config_path)

    # 0. Cleanup log vecchi
    cleanup_old_logs(config.logging)

    logger.info("Avvio scansione Minerva")
    if dry_run:
        logger.info("MODALITA' DRY-RUN: nessuna modifica al database")
    if regenerate:
        logger.info("MODALITA' RIGENERATIVA: tutti i documenti verranno riscansionati da zero")
    if filter_path:
        logger.info("FILTRO PERCORSO: %s", filter_path)

    # 2. Backup database
    if config.database.backup_enabled and not dry_run:
        backup = backup_database(config.database.path, config.database.backup_path)
        if backup:
            logger.info("Backup creato: %s", backup)

    # 3. Inizializza database
    conn = init_database(config.database.path)

    # Sincronizza aree da config
    if config.classificazione.aree:
        sync_aree_from_config(
            conn, [(a.codice, a.descrizione) for a in config.classificazione.aree]
        )
        conn.commit()

    doc_repo = DocumentRepository(conn)
    cliente_repo = ClienteRepository(conn)
    lookup_repo = LookupRepository(conn)

    # Carica mappa cod_area -> id_area per auto-classificazione
    area_id_map = lookup_repo.get_area_id_map()

    # 3b. Scansione rigenerativa: cancella tutti i documenti e l'indice FTS
    if regenerate and not dry_run:
        doc_repo.fts_delete_all()
        deleted = doc_repo.delete_all_documents()
        conn.commit()
        logger.info("Rigenerazione: %d documenti rimossi dal database", deleted)

    # 4. Verifica Ollama
    ollama_ok = False
    if config.ollama.enabled:
        ollama_ok = check_ollama_available(config.ollama.base_url)
        if ollama_ok:
            logger.info("Ollama disponibile a %s (modello: %s)", config.ollama.base_url, config.ollama.model)
        else:
            logger.warning("Ollama non raggiungibile, classificazione AI disabilitata")

    # 5. Scansiona ogni percorso base
    all_found_percorsi: set[str] = set()
    all_file_hashes: dict[str, str] = {}

    for percorso_base in config.percorsi_base:
        base_path = Path(percorso_base.percorso)
        if not base_path.exists():
            msg = f"Percorso base non trovato: {base_path}"
            logger.error(msg)
            stats.errori.append(msg)
            continue

        logger.info("Scansione percorso base: %s (%s)", percorso_base.nome, base_path)

        if percorso_base.tipo == "clienti":
            _scan_clienti(
                base_path=base_path,
                percorso_base_str=str(base_path),
                config=config,
                doc_repo=doc_repo,
                cliente_repo=cliente_repo,
                stats=stats,
                all_found_percorsi=all_found_percorsi,
                all_file_hashes=all_file_hashes,
                ollama_ok=ollama_ok,
                dry_run=dry_run,
                filter_path=filter_path,
                area_id_map=area_id_map,
            )
        else:
            # Tipo "fip" o altri - tratta come singola directory
            _scan_single_directory(
                dir_path=base_path,
                percorso_base_str=str(base_path),
                cliente_nome=percorso_base.nome,
                config=config,
                doc_repo=doc_repo,
                cliente_repo=cliente_repo,
                stats=stats,
                all_found_percorsi=all_found_percorsi,
                all_file_hashes=all_file_hashes,
                ollama_ok=ollama_ok,
                dry_run=dry_run,
                filter_path=filter_path,
                area_id_map=area_id_map,
            )

    # 6. Segna come CAN/SPO i documenti non trovati (non in modalita' rigenerativa e senza filtro)
    if not dry_run and not regenerate and not filter_path:
        cancellati, spostati = doc_repo.mark_not_found_as_deleted(
            all_found_percorsi, all_file_hashes
        )
        stats.file_cancellati += cancellati
        stats.file_spostati += spostati
        conn.commit()

    # 7. Chiudi connessione
    conn.close()

    stats.tempo_totale_secondi = time.time() - start_time
    logger.info(stats.summary())
    return stats


def _scan_clienti(
    base_path: Path,
    percorso_base_str: str,
    config: MinervaConfig,
    doc_repo: DocumentRepository,
    cliente_repo: ClienteRepository,
    stats: ScanStats,
    all_found_percorsi: set[str],
    all_file_hashes: dict[str, str],
    ollama_ok: bool,
    dry_run: bool,
    filter_path: str | None = None,
    area_id_map: dict[str, int] | None = None,
) -> None:
    """Scansiona un percorso di tipo 'clienti': ogni sotto-cartella è un cliente."""
    try:
        client_dirs = sorted(
            [d for d in base_path.iterdir() if d.is_dir()],
            key=lambda d: d.name.lower(),
        )
    except PermissionError as e:
        msg = f"Accesso negato a {base_path}: {e}"
        logger.error(msg)
        stats.errori.append(msg)
        return

    # Se c'e' un filtro path, scansiona solo il cliente coinvolto
    if filter_path:
        filter_norm = filter_path.replace("\\", "/")
        filter_first = filter_norm.split("/")[0]
        client_dirs = [d for d in client_dirs if d.name.lower() == filter_first.lower()]
        if not client_dirs:
            # Potrebbe essere un percorso assoluto: prova a risolverlo
            abs_filter = Path(filter_path)
            if abs_filter.exists():
                try:
                    rel = abs_filter.relative_to(base_path)
                    filter_first = str(rel).replace("\\", "/").split("/")[0]
                    client_dirs = sorted(
                        [d for d in base_path.iterdir() if d.is_dir() and d.name.lower() == filter_first.lower()],
                        key=lambda d: d.name.lower(),
                    )
                except ValueError:
                    pass

    for client_dir in client_dirs:
        _scan_single_directory(
            dir_path=client_dir,
            percorso_base_str=percorso_base_str,
            cliente_nome=client_dir.name,
            config=config,
            doc_repo=doc_repo,
            cliente_repo=cliente_repo,
            stats=stats,
            all_found_percorsi=all_found_percorsi,
            all_file_hashes=all_file_hashes,
            ollama_ok=ollama_ok,
            dry_run=dry_run,
            filter_path=filter_path,
            area_id_map=area_id_map,
        )


def _scan_single_directory(
    dir_path: Path,
    percorso_base_str: str,
    cliente_nome: str,
    config: MinervaConfig,
    doc_repo: DocumentRepository,
    cliente_repo: ClienteRepository,
    stats: ScanStats,
    all_found_percorsi: set[str],
    all_file_hashes: dict[str, str],
    ollama_ok: bool,
    dry_run: bool,
    filter_path: str | None = None,
    area_id_map: dict[str, int] | None = None,
) -> None:
    """Scansiona una singola directory cliente."""
    logger.info("Scansione cliente: %s", cliente_nome)
    stats.clienti_processati += 1

    # Carica filtro locale (censimento_filtro.json)
    filtro_locale = load_censimento_filtro(
        dir_path, config.scanner.filtro_globale_default
    )
    if filtro_locale is None:
        # Nessun censimento_filtro.json -> usa default globali
        filtro_locale = {
            "directory_da_leggere": ["/*"],
            "directory_da_evitare": [],
            "formati_da_leggere": config.scanner.filtro_globale_default.formati_da_leggere,
            "filtro_data": config.scanner.filtro_globale_default.filtro_data,
        }

    # Assicura che il cliente esista nel DB
    if not dry_run:
        cliente_repo.ensure_cliente(cliente_nome, config.scanner.utente_scanner)

    # Walk directory con filtri
    files = walk_client_directory(dir_path, filtro_locale, config.scanner.file_esclusi_regex)

    # Filtra per percorso specifico se richiesto
    if filter_path:
        filter_norm = filter_path.replace("\\", "/").lower()
        abs_filter = Path(filter_path)
        filtered = []
        for fp in files:
            # Match per percorso relativo
            rel = _compute_percorso_relativo(fp, percorso_base_str)
            if rel and rel.lower().startswith(filter_norm):
                filtered.append(fp)
            # Match per percorso assoluto
            elif abs_filter.is_absolute() and str(fp).replace("\\", "/").lower().startswith(str(abs_filter).replace("\\", "/").lower()):
                filtered.append(fp)
        files = filtered
        if not files:
            logger.info("Nessun file corrisponde al filtro '%s' in %s", filter_path, cliente_nome)
            return

    stats.file_trovati += len(files)

    # Raccogli tutti gli hash e percorsi correnti per questo cliente
    current_hashes: dict[str, str] = {}
    current_names: dict[str, str] = {}

    # Fase 1: calcolo hash per tutti i file
    logger.info("Fase 1: inizio calcolo hash per %d file", len(files))
    file_data_list: list[dict[str, Any]] = []
    for file_path in files:
        try:
            percorso_relativo = _compute_percorso_relativo(file_path, percorso_base_str)
            file_hash = compute_hash(file_path, config.scanner.hash_algorithm)

            if percorso_relativo:
                all_found_percorsi.add(percorso_relativo)
                if file_hash:
                    current_hashes[percorso_relativo] = file_hash
                    all_file_hashes[percorso_relativo] = file_hash
                current_names[percorso_relativo] = file_path.name

            file_data_list.append({
                "file_path": file_path,
                "percorso_relativo": percorso_relativo,
                "file_hash": file_hash,
            })
        except Exception as e:
            msg = f"Errore pre-processing {file_path}: {e}"
            logger.warning(msg)
            stats.file_con_errori += 1
            stats.errori.append(msg)

    # Fase 2: elaborazione di ogni file
    logger.info("Fase 1 completata. Fase 2: elaborazione di %d file", len(file_data_list))
    docs_for_revision: list[dict[str, Any]] = []

    for idx, fd in enumerate(file_data_list):
        file_path: Path = fd["file_path"]
        percorso_relativo: str = fd["percorso_relativo"]
        file_hash: str | None = fd["file_hash"]

        if not percorso_relativo:
            continue

        if idx % 100 == 0:
            logger.info("Elaborazione file %d/%d: %s", idx+1, len(file_data_list), file_path.name)

        try:
            doc_data = _process_single_file(
                file_path=file_path,
                percorso_relativo=percorso_relativo,
                percorso_base_str=percorso_base_str,
                cliente_nome=cliente_nome,
                file_hash=file_hash,
                current_hashes=current_hashes,
                current_names=current_names,
                config=config,
                doc_repo=doc_repo,
                ollama_ok=ollama_ok,
                dry_run=dry_run,
                stats=stats,
                area_id_map=area_id_map,
            )
            if doc_data:
                docs_for_revision.append(doc_data)

        except Exception as e:
            msg = f"Errore elaborazione {file_path.name}: {e}"
            logger.warning(msg)
            stats.file_con_errori += 1
            stats.errori.append(msg)

    # Fase 3: rilevamento revisioni
    # Deduplica per id_documento (lo stesso file potrebbe apparire 2 volte
    # se il walker lo trova da percorsi diversi)
    if docs_for_revision and not dry_run:
        seen_ids: set[int] = set()
        unique_docs: list[dict[str, Any]] = []
        for d in docs_for_revision:
            if d["id_documento"] not in seen_ids:
                seen_ids.add(d["id_documento"])
                unique_docs.append(d)
        _process_revisions(unique_docs, doc_repo, stats)

    # Commit dopo ogni cliente
    if not dry_run:
        doc_repo.conn.commit()

    logger.info("Cliente %s completato: %d file elaborati", cliente_nome, len(file_data_list))


def _process_single_file(
    file_path: Path,
    percorso_relativo: str,
    percorso_base_str: str,
    cliente_nome: str,
    file_hash: str | None,
    current_hashes: dict[str, str],
    current_names: dict[str, str],
    config: MinervaConfig,
    doc_repo: DocumentRepository,
    ollama_ok: bool,
    dry_run: bool,
    stats: ScanStats,
    area_id_map: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Elabora un singolo file: metadati, status, tag, AI, inserimento/aggiornamento DB.

    Restituisce i dati del documento per l'analisi revisioni, o None in caso di errore.
    """
    # Metadati filesystem
    try:
        stat = file_path.stat()
        fs_meta = {
            "documento_data_creazione": datetime.fromtimestamp(stat.st_ctime).isoformat(sep=" ", timespec="seconds"),
            "documento_data_ultima_modifica": datetime.fromtimestamp(stat.st_mtime).isoformat(sep=" ", timespec="seconds"),
            "documento_dimensione": stat.st_size,
            "documento_estensione": file_path.suffix.lower(),
        }
    except OSError as e:
        logger.warning("Impossibile leggere stat di %s: %s", file_path, e)
        return None

    # Controlla se il file esiste già nel DB
    existing = doc_repo.find_by_percorso_relativo(percorso_relativo)

    if existing:
        # Documento esistente: determina stato
        stato = determine_status_existing(
            record_db=existing,
            file_exists=True,
            current_hash=file_hash,
            all_current_hashes=current_hashes,
            all_current_names=current_names,
        )

        if stato == "MOD":
            stats.file_modificati += 1
        elif stato == "EXD":
            stats.file_duplicati += 1

        if not dry_run:
            updates = {
                "documento_hash": file_hash,
                "stato": stato,
                "ultimo_censimento_utente": config.scanner.utente_scanner,
                **fs_meta,
            }

            testo_contenuto = None
            aree_suggerite: list[str] = []
            # Estrai metadati contenuto solo se modificato
            if stato == "MOD":
                content_meta, testo_contenuto, aree_suggerite = _extract_and_enrich(
                    file_path, percorso_relativo, file_path.name,
                    config, ollama_ok, stats,
                )
                updates.update(content_meta)

            doc_repo.update_scan_fields(percorso_relativo, updates)

            # Aggiorna indice FTS se il file è modificato
            if stato == "MOD":
                doc_repo.fts_index_document(existing["id_documento"], {
                    "documento_nome_file": file_path.name,
                    "documento_titolo": updates.get("documento_titolo") or existing.get("documento_titolo") or "",
                    "testo_contenuto": testo_contenuto or "",
                    "documento_parole_chiave": updates.get("documento_parole_chiave") or existing.get("documento_parole_chiave") or "",
                    "titoli_estratti": updates.get("titoli_estratti") or existing.get("titoli_estratti") or "",
                    "indice_contenuti": updates.get("indice_contenuti") or existing.get("indice_contenuti") or "",
                    "sommario_estratto": updates.get("sommario_estratto") or existing.get("sommario_estratto") or "",
                })

            # Applica aree auto-rilevate alla tabella M2M (solo se non ci sono già)
            if aree_suggerite and area_id_map:
                doc_repo.set_auto_classifications(
                    existing["id_documento"], aree_suggerite, area_id_map
                )

        return {
            "id_documento": existing["id_documento"],
            "documento_nome_file": file_path.name,
            "percorso_relativo": percorso_relativo,
            "documento_data_creazione": fs_meta["documento_data_creazione"],
            "documento_data_ultima_modifica": fs_meta["documento_data_ultima_modifica"],
        }

    else:
        # Documento nuovo
        existing_by_hash = doc_repo.find_by_hash_and_name(file_hash, file_path.name) if file_hash else []
        stato = determine_status_new(file_hash, file_path.name, existing_by_hash)

        if stato == "DUP":
            stats.file_duplicati += 1
        else:
            stats.file_nuovi += 1

        if not dry_run:
            # Estrai metadati contenuto
            content_meta, testo_contenuto, aree_suggerite = _extract_and_enrich(
                file_path, percorso_relativo, file_path.name,
                config, ollama_ok, stats,
            )

            # Revisione dal nome file o dalla posizione in cartella "old"
            rev_info = parse_revision(file_path.name)
            doc_revision = None
            if rev_info:
                if rev_info.is_old:
                    doc_revision = "OLD"
                elif rev_info.revisione:
                    doc_revision = rev_info.revisione
            if not doc_revision and is_in_old_folder(percorso_relativo):
                doc_revision = "OLD"

            doc_record = {
                "cliente_cartella": cliente_nome,
                "percorso_base": percorso_base_str,
                "percorso_relativo": percorso_relativo,
                "documento_nome_file": file_path.name,
                "documento_hash": file_hash,
                "stato": stato,
                "documento_revisione": doc_revision,
                **fs_meta,
                **content_meta,
                "inserimento_utente": config.scanner.utente_scanner,
            }

            new_id = doc_repo.insert_document(doc_record)

            # Indicizza nel full-text search
            doc_repo.fts_index_document(new_id, {
                "documento_nome_file": file_path.name,
                "documento_titolo": content_meta.get("documento_titolo") or "",
                "testo_contenuto": testo_contenuto or "",
                "documento_parole_chiave": content_meta.get("documento_parole_chiave") or "",
                "titoli_estratti": content_meta.get("titoli_estratti") or "",
                "indice_contenuti": content_meta.get("indice_contenuti") or "",
                "sommario_estratto": content_meta.get("sommario_estratto") or "",
            })

            # Applica aree auto-rilevate alla tabella M2M
            if aree_suggerite and area_id_map:
                doc_repo.set_auto_classifications(new_id, aree_suggerite, area_id_map)

            return {
                "id_documento": new_id,
                "documento_nome_file": file_path.name,
                "percorso_relativo": percorso_relativo,
                "documento_data_creazione": fs_meta["documento_data_creazione"],
                "documento_data_ultima_modifica": fs_meta["documento_data_ultima_modifica"],
            }

        return None


def _extract_and_enrich(
    file_path: Path,
    percorso_relativo: str,
    filename: str,
    config: MinervaConfig,
    ollama_ok: bool,
    stats: ScanStats,
) -> tuple[dict[str, Any], str | None, list[str]]:
    """Estrae metadati contenuto, auto-tag, e classificazione AI.

    Restituisce (campi_da_aggiornare, testo_contenuto_per_fts, aree_suggerite).
    """
    result: dict[str, Any] = {}

    # 1. Estrazione metadati dal contenuto
    meta = extract_metadata(file_path)
    result["autore"] = meta.get("autore")
    result["autore_ultima_modifica"] = meta.get("autore_ultima_modifica")
    result["versione_interna"] = meta.get("versione_interna")
    result["documento_titolo"] = meta.get("documento_titolo")
    result["documento_parole_chiave"] = meta.get("documento_parole_chiave")
    result["titoli_estratti"] = meta.get("titoli_estratti")
    result["indice_contenuti"] = meta.get("indice_contenuti")
    result["sommario_estratto"] = meta.get("sommario_estratto")

    # 2. Auto-tag da percorso, nome file e contenuto
    path_tags = auto_tag_from_path(percorso_relativo)
    filename_tags = auto_tag_from_filename(filename)

    # Analisi contenuto per rilevamento area
    testo_contenuto = meta.get("testo_contenuto")
    content_tags = auto_tag_from_content(
        testo_contenuto=testo_contenuto,
        titoli_estratti=meta.get("titoli_estratti"),
        indice_contenuti=meta.get("indice_contenuti"),
        documento_titolo=meta.get("documento_titolo"),
        documento_parole_chiave=meta.get("documento_parole_chiave"),
        sommario_estratto=meta.get("sommario_estratto"),
    )

    merged_tags = merge_auto_tags(path_tags, filename_tags, content_tags)

    # Salva FIP suggeriti come stringa separata da virgola
    if merged_tags["fip_suggeriti"]:
        result["fip"] = ",".join(merged_tags["fip_suggeriti"])

    # Salva i metadati AI/auto come JSON
    auto_meta = {}
    if merged_tags["aree_suggerite"]:
        auto_meta["aree_suggerite"] = merged_tags["aree_suggerite"]
    if merged_tags.get("aree_scores"):
        auto_meta["aree_scores"] = merged_tags["aree_scores"]
    if merged_tags["tipo_doc_suggerito"]:
        auto_meta["tipo_doc_suggerito"] = merged_tags["tipo_doc_suggerito"]

    # 3. Classificazione AI con Ollama
    if ollama_ok and testo_contenuto and testo_contenuto.strip():
        ai_result = classify_document(
            testo=testo_contenuto,
            base_url=config.ollama.base_url,
            model=config.ollama.model,
            timeout=config.ollama.timeout_seconds,
            max_chars=config.ollama.max_text_chars,
            filename=filename,
        )
        if ai_result:
            stats.classificazioni_ai += 1

            # Parole chiave AI (aggiungi a quelle esistenti)
            ai_keywords = ai_result.get("parole_chiave", [])
            if ai_keywords:
                existing_kw = result.get("documento_parole_chiave") or ""
                all_kw = set(existing_kw.split(",")) if existing_kw else set()
                all_kw.update(ai_keywords)
                all_kw.discard("")
                result["documento_parole_chiave"] = ",".join(sorted(all_kw))

            # Riassunto AI
            ai_summary = ai_result.get("riassunto")
            if ai_summary:
                result["sommario_estratto"] = ai_summary

            # Aree suggerite dall'AI
            ai_aree = ai_result.get("aree_suggerite", [])
            if ai_aree:
                auto_meta["aree_suggerite_ai"] = ai_aree

            # Tipo documento suggerito dall'AI
            ai_tipo = ai_result.get("tipo_documento_suggerito")
            if ai_tipo:
                auto_meta["tipo_doc_suggerito_ai"] = ai_tipo

    # Salva auto_meta come JSON nel campo metadati_json
    if auto_meta:
        result["metadati_json"] = json.dumps(auto_meta, ensure_ascii=False)

    return result, testo_contenuto, merged_tags.get("aree_suggerite", [])


def _process_revisions(
    docs: list[dict[str, Any]],
    doc_repo: DocumentRepository,
    stats: ScanStats,
) -> None:
    """Raggruppa i documenti per revisione e aggiorna id_documento_principale."""
    # Reset: azzera id_documento_principale per tutti i documenti coinvolti
    # per evitare riferimenti stantii da raggruppamenti precedenti
    for doc in docs:
        doc_repo.update_documento_principale(doc["id_documento"], None)

    groups = group_revisions(docs)

    for group in groups:
        if len(group) < 2:
            continue

        stats.revisioni_rilevate += 1

        # Il primo documento del gruppo e' il principale (revisione piu' recente, non .old)
        principale = group[0]
        id_principale = principale["id_documento"]

        for doc in group[1:]:
            if doc["id_documento"] == id_principale:
                continue  # Evita auto-riferimenti
            doc_repo.update_documento_principale(doc["id_documento"], id_principale)
            logger.debug(
                "Revisione: %s -> principale %s",
                doc["documento_nome_file"],
                principale["documento_nome_file"],
            )


def _compute_percorso_relativo(file_path: Path, percorso_base: str) -> str | None:
    """Calcola il percorso relativo rispetto al percorso base."""
    try:
        base = Path(percorso_base)
        rel = file_path.relative_to(base)
        # Usa forward slash per uniformità
        return str(rel).replace("\\", "/")
    except ValueError:
        logger.warning(
            "Impossibile calcolare percorso relativo: %s non è sotto %s",
            file_path, percorso_base,
        )
        return None
