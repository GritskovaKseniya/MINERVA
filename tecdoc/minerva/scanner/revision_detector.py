"""Rilevamento revisioni di documenti (.R00/.R01, .old, _new, _copia, cartelle old)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Pattern 1: .R{NN} (es. file.R00.docx, file.R01.pdf)
RE_REVISION_DOT = re.compile(r"^(.+)\.R(\d{2,})\.(\w+)$", re.IGNORECASE)

# Pattern 1b: _R{N} (es. file_R2.docx)
RE_REVISION_UNDERSCORE = re.compile(r"^(.+)_R(\d+)\.(\w+)$", re.IGNORECASE)

# Pattern 2a: .old.{ext} (es. file.old.docx)
RE_OLD_BEFORE_EXT = re.compile(r"^(.+)\.old\.(\w+)$", re.IGNORECASE)

# Pattern 2b: .{ext}.old (es. file.docx.old)
RE_OLD_AFTER_EXT = re.compile(r"^(.+\.(\w+))\.old$", re.IGNORECASE)

# Pattern 3: "new" nel nome come parola separata (es. doc_new.docx, doc new.pdf, doc.new.xlsx)
# Richiede un separatore (_/spazio/.) prima di "new"
RE_NEW_IN_NAME = re.compile(
    r"^(.*?)[_\s.]new(?=[_\s.]|$)(.*?)\.(\w+)$",
    re.IGNORECASE,
)

# Pattern 4: "copia" nel nome come parola separata (es. doc - Copia.docx, doc_copia.pdf)
# I file con "copia" sono SEMPRE revisioni superate
RE_COPIA_IN_NAME = re.compile(
    r"^(.*?)[\s_.\-]+copia(?:[\s_.\-]+\(?\d*\)?)?(?=[_\s.\-]|$)(.*?)\.(\w+)$",
    re.IGNORECASE,
)
# Pattern 4b: suffisso " - Copia" generato da Windows (es. "doc - Copia.docx", "doc - Copia (2).docx")
RE_COPIA_WINDOWS = re.compile(
    r"^(.+?)\s*-\s*Copia(?:\s*\(\d+\))?\.(\w+)$",
    re.IGNORECASE,
)


@dataclass
class RevisionInfo:
    """Informazioni sulla revisione estratte dal nome file."""
    nome_base: str
    revisione: str | None  # "00", "01", "OLD", None
    is_old: bool
    estensione: str


def parse_revision(filename: str) -> RevisionInfo | None:
    """Analizza il nome file per estrarre informazioni sulla revisione.

    Restituisce None se il file non corrisponde a nessun pattern di revisione.
    Riconosce: .R00/.R01, _R1, .old, _new, new_, copia.
    """
    # Pattern 2a: .old.{ext} (controllare PRIMA dei pattern .R per gestire file.R01.old.docx)
    m = RE_OLD_BEFORE_EXT.match(filename)
    if m:
        base = m.group(1)
        ext = m.group(2)
        # Controlla se il base stesso ha una revisione (es. file.R01.old.docx -> base="file.R01")
        inner = RE_REVISION_DOT.match(base + ".dummy")
        rev = None
        if inner:
            # Caso: file.R01.old.docx -> base=file, rev=01, is_old=True
            base = inner.group(1)
            rev = inner.group(2)
        return RevisionInfo(nome_base=base, revisione=rev, is_old=True, estensione=ext)

    # Pattern 2b: .{ext}.old
    m = RE_OLD_AFTER_EXT.match(filename)
    if m:
        full_without_old = m.group(1)
        ext = m.group(2)
        # Rimuovi l'estensione per ottenere il base
        base = full_without_old.rsplit(".", 1)[0] if "." in full_without_old else full_without_old
        return RevisionInfo(nome_base=base, revisione=None, is_old=True, estensione=ext)

    # Pattern 1: .R{NN}
    m = RE_REVISION_DOT.match(filename)
    if m:
        return RevisionInfo(
            nome_base=m.group(1),
            revisione=m.group(2),
            is_old=False,
            estensione=m.group(3),
        )

    # Pattern 1b: _R{N}
    m = RE_REVISION_UNDERSCORE.match(filename)
    if m:
        return RevisionInfo(
            nome_base=m.group(1),
            revisione=m.group(2),
            is_old=False,
            estensione=m.group(3),
        )

    # Pattern 3: "new" nel nome
    new_base = _strip_new_from_filename(filename)
    if new_base is not None:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        return RevisionInfo(
            nome_base=new_base,
            revisione=None,
            is_old=False,  # "new" non è old, la data di creazione determina quale è attuale
            estensione=ext,
        )

    # Pattern 4: "copia" nel nome (sempre revisione superata)
    copia_base = _strip_copia_from_filename(filename)
    if copia_base is not None:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        return RevisionInfo(
            nome_base=copia_base,
            revisione=None,
            is_old=True,  # "copia" è SEMPRE una revisione superata
            estensione=ext,
        )

    return None


def _strip_new_from_filename(filename: str) -> str | None:
    """Rimuove 'new' dal nome file se presente come parola distinta.

    Restituisce il nome base (senza estensione) o None se "new" non trovato.

    Esempi:
        "doc_new.docx"       -> "doc"
        "doc new.pdf"        -> "doc"
        "doc.new.xlsx"       -> "doc"
        "doc_new_v2.docx"    -> "doc_v2"
        "new_doc.docx"       -> "doc"
        "newsletter.docx"    -> None (new è parte di newsletter)
    """
    m = RE_NEW_IN_NAME.match(filename)
    if not m:
        return None

    before = m.group(1)  # parte prima di [sep]new
    after = m.group(2) or ""  # parte dopo new (opzionale)
    # Ricostruisci il base: before + after
    base = before + after
    # Pulisci separatori iniziali/finali residui
    base = base.strip("_. ")
    return base if base else None


def _strip_copia_from_filename(filename: str) -> str | None:
    """Rimuove 'copia' dal nome file se presente come parola distinta.

    Restituisce il nome base (senza estensione) o None se "copia" non trovato.

    Esempi:
        "doc - Copia.docx"       -> "doc"
        "doc - Copia (2).docx"   -> "doc"
        "doc_copia.pdf"          -> "doc"
        "doc copia.xlsx"         -> "doc"
        "copialettere.docx"      -> None (copia è parte di copialettere)
    """
    # Prova prima il pattern Windows " - Copia"
    m = RE_COPIA_WINDOWS.match(filename)
    if m:
        base = m.group(1).strip()
        return base if base else None

    # Poi il pattern generico
    m = RE_COPIA_IN_NAME.match(filename)
    if not m:
        return None

    before = m.group(1)
    after = m.group(3)  # dopo copia, prima dell'estensione
    # Ignora il match se "copia" è parte di una parola (es. "copialettere")
    # Il regex richiede un separatore prima, quindi questo caso è già gestito
    base = before
    if m.group(2):  # parti dopo "copia" prima dell'estensione
        base = before + m.group(2)
    base = base.strip("_.- ")
    return base if base else None


def is_in_old_folder(percorso_relativo: str) -> bool:
    """Verifica se il file si trova in una cartella 'old'."""
    parts = percorso_relativo.replace("\\", "/").split("/")
    # Controlla solo le directory (non il nome file)
    return any(part.lower() == "old" for part in parts[:-1])


def _get_base_name(filename: str) -> str:
    """Calcola il nome base per il raggruppamento (senza estensione)."""
    rev_info = parse_revision(filename)
    if rev_info:
        return rev_info.nome_base.lower()
    # Nessun pattern di revisione: usa il nome senza estensione
    return (filename.rsplit(".", 1)[0] if "." in filename else filename).lower()


def group_revisions(documents: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Raggruppa i documenti per revisione.

    Ogni gruppo è una lista di documenti correlati (revisioni dello stesso file).
    Il primo elemento di ogni gruppo è il documento principale (più recente).

    Gestisce:
    - Pattern .R00/.R01 e _R1 (numerazione revisioni)
    - Pattern .old nel nome file
    - Pattern "new" nel nome file (raggruppato con versione senza "new")
    - File in cartelle "old" (versioni precedenti)
    - File con "copia" nel nome (sempre revisioni superate)
    - File con lo stesso nome in directory diverse (il più recente è il principale)

    Args:
        documents: Lista di dict con almeno 'documento_nome_file', 'id_documento',
                   'percorso_relativo', 'documento_data_ultima_modifica'.

    Returns:
        Lista di gruppi. Ogni gruppo ha il principale come primo elemento.
    """
    # Fase 1: calcola chiave di raggruppamento per ogni documento
    entries: list[tuple[dict[str, Any], str, bool, RevisionInfo | None]] = []

    for doc in documents:
        filename = doc["documento_nome_file"]
        percorso = doc.get("percorso_relativo", "")
        in_old = is_in_old_folder(percorso)

        rev_info = parse_revision(filename)
        if rev_info:
            base_name = rev_info.nome_base.lower()
            ext = rev_info.estensione.lower()
            old = rev_info.is_old or in_old
        else:
            if "." in filename:
                base_name, ext = filename.rsplit(".", 1)
                base_name = base_name.lower()
                ext = ext.lower()
            else:
                base_name = filename.lower()
                ext = ""
            old = in_old

        # Chiave: nome base + estensione (per non raggruppare file con estensioni diverse)
        group_key = f"{base_name}||{ext}"

        entries.append((doc, group_key, old, rev_info))

    # Fase 2: raggruppa per chiave
    groups: dict[str, list[tuple[dict[str, Any], bool, RevisionInfo | None]]] = {}
    for doc, group_key, old, rev_info in entries:
        groups.setdefault(group_key, []).append((doc, old, rev_info))

    # Fase 3: ordina all'interno di ogni gruppo e produci output
    result: list[list[dict[str, Any]]] = []

    for group_key, group in groups.items():
        if len(group) < 2:
            doc = group[0][0]
            rev_info = group[0][2]
            if rev_info:
                doc["_revision_info"] = {
                    "revisione": rev_info.revisione,
                    "is_old": group[0][1],
                    "nome_base": rev_info.nome_base,
                }
            result.append([doc])
            continue

        # Ordina: non-old prima, poi revisione decrescente, poi data creazione decrescente
        sorted_group = sorted(
            group,
            key=lambda x: (
                not x[1],  # Non-old prima (True > False, negato)
                _revision_sort_key(x[2].revisione if x[2] else None),
                x[0].get("documento_data_ultima_modifica", "") or x[0].get("documento_data_creazione", "") or "",
            ),
            reverse=True,
        )

        ordered_docs = []
        for doc, old, rev_info in sorted_group:
            doc["_revision_info"] = {
                "revisione": rev_info.revisione if rev_info else None,
                "is_old": old,
                "nome_base": rev_info.nome_base if rev_info else group_key.split("||")[0],
            }
            ordered_docs.append(doc)

        result.append(ordered_docs)

    return result


def _revision_sort_key(revision: str | None) -> int:
    """Chiave di ordinamento per le revisioni. Più alto = più recente.

    File senza numero di revisione (None) = versione corrente, ha priorità massima.
    """
    if revision is None:
        return 999999  # Senza numero revisione = versione corrente
    try:
        return int(revision)
    except ValueError:
        return -1
