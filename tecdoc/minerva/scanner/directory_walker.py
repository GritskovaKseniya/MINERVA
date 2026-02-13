"""Lettura filesystem con filtri basati su censimento_filtro.json."""

from __future__ import annotations

import fnmatch
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from minerva.config.settings import FiltroData

logger = logging.getLogger(__name__)


def walk_client_directory(
    client_path: Path,
    filtro: dict[str, Any],
    file_esclusi_regex: list[str] | None = None,
) -> list[Path]:
    """Scansiona la directory di un cliente applicando i filtri.

    Args:
        client_path: Percorso della cartella cliente.
        filtro: Dizionario con i filtri (da censimento_filtro.json + merge globale).

    Returns:
        Lista di Path dei file trovati.
    """
    dir_include = filtro.get("directory_da_leggere", ["/*"])
    dir_exclude = filtro.get("directory_da_evitare", [])
    formati = filtro.get("formati_da_leggere", ["*"])
    filtro_data: FiltroData = filtro.get("filtro_data", FiltroData())

    # Calcola il range di date se necessario
    data_min = _compute_date_min(filtro_data)

    # Compila i pattern regex per esclusione file
    compiled_esclusi = _compile_esclusi(file_esclusi_regex or [])

    files: list[Path] = []

    if "/*" in dir_include or "*" in dir_include:
        # Leggi tutto ricorsivamente dalla root del cliente
        search_dirs = [client_path]
    else:
        search_dirs = []
        for d in dir_include:
            target = client_path / d
            if target.exists() and target.is_dir():
                search_dirs.append(target)

    for search_dir in search_dirs:
        if _is_excluded(search_dir, client_path, dir_exclude):
            logger.debug("Directory esclusa: %s", search_dir)
            continue

        try:
            for item in search_dir.rglob("*"):
                if not item.is_file():
                    continue
                if _is_file_excluded(item.name, compiled_esclusi):
                    continue
                if _is_excluded(item.parent, client_path, dir_exclude):
                    continue
                if not _matches_format(item.name, formati):
                    continue
                if data_min and not _matches_date(item, data_min):
                    continue
                files.append(item)
        except PermissionError as e:
            logger.warning("Accesso negato a %s: %s", search_dir, e)

    logger.info("Cliente %s: trovati %d file", client_path.name, len(files))
    return files


def _is_excluded(dir_path: Path, client_root: Path, exclude_list: list[str]) -> bool:
    """Controlla se una directory è nella lista di esclusione."""
    try:
        rel = dir_path.relative_to(client_root)
    except ValueError:
        return False

    rel_str = str(rel).replace("\\", "/")
    for excl in exclude_list:
        excl_normalized = excl.replace("\\", "/")
        if rel_str == excl_normalized or rel_str.startswith(excl_normalized + "/"):
            return True
    return False


def _matches_format(filename: str, formati: list[str]) -> bool:
    """Controlla se il file corrisponde ai formati configurati."""
    if "*" in formati:
        return True
    return any(fnmatch.fnmatch(filename.lower(), fmt.lower()) for fmt in formati)


def _compute_date_min(filtro_data: FiltroData) -> datetime | None:
    """Calcola la data minima per il filtro temporale."""
    if filtro_data.usa_giorni_all_indietro and filtro_data.giorni_all_indietro:
        return datetime.now() - timedelta(days=filtro_data.giorni_all_indietro)
    if filtro_data.data_inizio:
        try:
            return datetime.fromisoformat(filtro_data.data_inizio)
        except ValueError:
            logger.warning("data_inizio non valida: %s", filtro_data.data_inizio)
    return None


def _compile_esclusi(patterns: list[str]) -> list[re.Pattern]:
    """Compila i pattern regex per esclusione file, scartando quelli non validi."""
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            logger.warning("Pattern regex non valido '%s': %s", p, e)
    return compiled


def _is_file_excluded(filename: str, patterns: list[re.Pattern]) -> bool:
    """Controlla se il nome file corrisponde a uno dei pattern di esclusione."""
    return any(p.search(filename) for p in patterns)


def _matches_date(file_path: Path, data_min: datetime) -> bool:
    """Controlla se la data di ultima modifica del file è >= data_min."""
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return mtime >= data_min
    except OSError:
        return True  # In caso di errore, includiamo il file
