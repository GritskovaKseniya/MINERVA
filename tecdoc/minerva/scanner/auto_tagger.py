"""Auto-classificazione da nome file, percorso cartella e contenuto documento."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Regole FIP basate sui nomi delle cartelle (case-insensitive)
FIP_FOLDER_RULES: list[tuple[str, str]] = [
    (r"project.*management", "PRJM"),
    (r"engineering", "ENGR"),
    (r"visioning", "VISN"),
    (r"training", "TRNG"),
    (r"pilot", "PILT"),
    (r"test(?:ing)?(?:\b|$)", "TEST"),
    (r"tuning", "TUNG"),
    (r"support", "SUPP"),
]

# ---------------------------------------------------------------------------
# Regole Area basate sul nome file (case-insensitive, regex)
# Ogni riga: (pattern_regex, [lista_codici_area])
# ---------------------------------------------------------------------------
AREA_FILENAME_RULES: list[tuple[str, list[str]]] = [
    # MES & MOM
    (r"\bmes\b|\bmom\b|\bmanufacturing.?execution\b|\bmanufacturing.?operation", ["MES"]),
    (r"\bavanzamento.?produz|\bdichiarazion[ei].?produz|\bwork.?order\b|\bordine.?di.?lavoro", ["MES"]),
    # APS
    (r"\baps\b|\bplanning\b|\bscheduling\b|\bpianificazione\b|\bschedulazione\b", ["APS"]),
    (r"\bdemand.?plan|\bforecast|\bprevisione.?domanda", ["APS"]),
    # BI - Business Intelligence
    (r"\bbusiness.?intelligence\b|\b[bB][iI]\b(?=.*(?:analys|report|olap|cube|data))", ["BI"]),
    (r"\bolap\b|\bcube\b|\bdatawarehouse\b|\bdata.?warehouse\b|\bdata.?mart\b", ["BI"]),
    # FLEX3
    (r"\bflex\s?3\b|\bjflex\b", ["FLEX3"]),
    # IND - Industry 4.0 / 5.0
    (r"\bindustry\b|\b4\.0\b|\b5\.0\b|\biot\b|\binterconness", ["IND"]),
    (r"\bplc\b|\bopc[\s\-]?ua\b|\bscada\b|\bgateway\b", ["IND"]),
    # INT - Integrazione
    (r"\bintegrazion[ei]\b|\binterface\b|\bmiddleware\b", ["INT"]),
    (r"\bsap\b|\berp\b|\bgestionale\b|\bedi\b|\bedifact\b|\bwebservice\b|\bweb.?service\b", ["INT"]),
    # JAD - Dashboard
    (r"\bjad\b|\badvanced.?dashboard\b|\bcruscott[oi]\b", ["JAD"]),
    # KPI
    (r"\bkpi\b|\bindicator[ei]\b|\bperformance\b|\brendiment", ["KPI"]),
    # MAN - Manutenzione
    (r"\bmanutenzione\b|\bmaintenance\b|\bmtbf\b|\bmttr\b", ["MAN"]),
    (r"\bpreventiva\b|\bcorrettiva\b|\bmanut[.\s]", ["MAN"]),
    # MCS - Manufacturing Control System
    (r"\bmcs\b|\bmanufacturing.?control\b|\bcontrollo.?produzion", ["MCS"]),
    # NC - Non Conformità
    (r"\bnon.?conformit[aà]\b|\bnonconformit[aà]\b|\breclam[oi]\b", ["NC"]),
    (r"\bscart[oi]\b|\banomali[ae]\b|\bdifett[oi]\b", ["NC"]),
    # OPM - Operation Management
    (r"\bopm\b|\boperation.?management\b", ["OPM"]),
    (r"\bacquist[oi]\b|\briceviment[oi]\b", ["OPM"]),
    # POR - Porting
    (r"\bporting\b|\bmigrazion[ei]\b|\bupgrade\b|\baggiornament[oi]\b", ["POR"]),
    # QLT - Qualità
    (r"\bqualit[aà]\b|\bquality\b|\bspc\b|\bcollaud[oi]\b", ["QLT"]),
    (r"\bcertificazion[ei]\b|\baudit\b|\bcontrollo.?qualit", ["QLT"]),
    # REP - Reportistica/Stampe
    (r"\breport(?:istic[ao])?\b|\bstamp[ae]\b|\bjasper\b|\bcrystal\b", ["REP"]),
    (r"\bmodulo.?stamp[ae]\b|\btemplate.?stamp", ["REP"]),
    # SCC - Supply Chain
    (r"\bsupply.?chain\b|\bscc\b|\bapprovvigionament[oi]\b", ["SCC"]),
    (r"\bfornitore\b|\bvendor\b", ["SCC"]),
    # SEQ - Sequenziatore
    (r"\bsequenziat|\bsequencing\b|\bsequenza.?produz", ["SEQ"]),
    # SFC - Smart Factory Console
    (r"\bsmart.?factory\b|\bsfc\b|\bconsole.?fabbrica", ["SFC"]),
    # SI - Standard Interface
    (r"\bstandard.?interface\b|\b[sS][iI]_|\b_[sS][iI]\b", ["SI"]),
    # SQL
    (r"\bsql\b|\bquery\b|\bstored.?proc|\btrigger\b|\bview\b", ["SQL"]),
    # SYS - Sistemistica
    (r"\bsistemistic[ao]\b|\binstallazion[ei]\b|\bconfigurazion[ei]\b", ["SYS"]),
    (r"\binfrastruttur[ae]\b|\bserver\b|\bhardware\b", ["SYS"]),
    # WMS - Warehouse
    (r"\bwms\b|\bwarehouse\b|\bmagazzin[oi]\b|\bpicking\b|\bstoccaggio\b|\bubicazion[ei]\b", ["WMS"]),
]

# ---------------------------------------------------------------------------
# Regole Area basate sul percorso cartelle (case-insensitive)
# Ogni riga: (pattern_regex, [lista_codici_area])
# ---------------------------------------------------------------------------
AREA_PATH_RULES: list[tuple[str, list[str]]] = [
    (r"\bmes\b|\bmom\b", ["MES"]),
    (r"\baps\b", ["APS"]),
    (r"\bbi\b", ["BI"]),
    (r"\bflex\s?3\b|\bjflex\b", ["FLEX3"]),
    (r"\bindustry|\bindustria|\biot\b|\binterconness", ["IND"]),
    (r"\bintegrazion|\binterface\b|\bsap\b|\berp\b", ["INT"]),
    (r"\bjad\b|\bdashboard\b|\bcruscott", ["JAD"]),
    (r"\bkpi\b", ["KPI"]),
    (r"\bmanutenzion|\bmaintenanc", ["MAN"]),
    (r"\bmcs\b", ["MCS"]),
    (r"\bnon.?conform|\breclam", ["NC"]),
    (r"\bopm\b", ["OPM"]),
    (r"\bporting\b|\bmigrazion|\bupgrade\b", ["POR"]),
    (r"\bqualit[aà]|\bquality\b", ["QLT"]),
    (r"\breport|\bstamp[ae]\b", ["REP"]),
    (r"\bsupply.?chain|\bscc\b", ["SCC"]),
    (r"\bsequenziat", ["SEQ"]),
    (r"\bsmart.?factory|\bsfc\b", ["SFC"]),
    (r"\bstandard.?interface", ["SI"]),
    (r"\bsql\b", ["SQL"]),
    (r"\bsistemistic|\bsysadmin|\binfrastruttur", ["SYS"]),
    (r"\bwms\b|\bwarehouse\b|\bmagazzin", ["WMS"]),
]

# ---------------------------------------------------------------------------
# Parole chiave per ricerca nel contenuto del documento (testo, titoli, TOC)
# Pattern più restrittivi con word boundary per evitare falsi positivi nel testo libero.
# Ogni riga: (codice_area, [lista_keyword_regex])
# ---------------------------------------------------------------------------
AREA_CONTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("MES", [
        r"\bmes\b", r"\bmom\b", r"\bmanufacturing execution",
        r"\bmanufacturing operation", r"\bavanzamento produzion",
        r"\bdichiarazione produzion", r"\bwork order\b", r"\bordine di lavoro",
        r"\bciclo di produzion", r"\bdistinta base\b", r"\bbom\b",
        r"\bshop ?floor\b", r"\breparto produttiv",
    ]),
    ("APS", [
        r"\baps\b", r"\badvanced planning", r"\bscheduling\b",
        r"\bpianificazione produzion", r"\bschedulazione\b",
        r"\bdemand planning\b", r"\bprevisione della domanda",
        r"\bcapacity planning\b", r"\bpianificazione capacit",
    ]),
    ("BI", [
        r"\bbusiness intelligence\b", r"\bolap\b", r"\bcube\b",
        r"\bdatawarehouse\b", r"\bdata warehouse\b", r"\bdata mart\b",
        r"\banalisi dati\b", r"\bdata analytics\b", r"\bdata mining\b",
    ]),
    ("FLEX3", [
        r"\bflex ?3\b", r"\bjflex\b",
    ]),
    ("IND", [
        r"\bindustry 4\.0\b", r"\bindustry 5\.0\b", r"\bindustria 4\.0\b",
        r"\biot\b", r"\binterconnession[ei]", r"\binterconnect",
        r"\bopc[- ]?ua\b", r"\bscada\b", r"\bplc\b",
        r"\bprotocollo macchina\b", r"\bgateway\b",
    ]),
    ("INT", [
        r"\bintegrazione\b", r"\bsistema gestionale\b", r"\bsap\b",
        r"\berp\b", r"\bedi\b", r"\bedifact\b",
        r"\bweb ?service\b", r"\brest ?api\b", r"\bsoap\b",
        r"\bmiddleware\b", r"\bconnettore\b",
    ]),
    ("JAD", [
        r"\bjad\b", r"\badvanced dashboard\b", r"\bcruscott[oi]\b",
        r"\bdashboard\b",
    ]),
    ("KPI", [
        r"\bkpi\b", r"\bindicator[ei] di prestazion",
        r"\bkey performance\b", r"\boee\b",
        r"\brendicontazione\b", r"\banalisi prestazion",
    ]),
    ("MAN", [
        r"\bmanutenzione\b", r"\bmaintenance\b",
        r"\bmanutenzione preventiva\b", r"\bmanutenzione correttiva\b",
        r"\bmtbf\b", r"\bmttr\b", r"\btpm\b",
        r"\bpiano di manutenzione\b",
    ]),
    ("MCS", [
        r"\bmcs\b", r"\bmanufacturing control\b",
        r"\bcontrollo di produzione\b", r"\bsistema di controllo produz",
    ]),
    ("NC", [
        r"\bnon conformit[aà]\b", r"\bnonconformit[aà]\b",
        r"\breclam[oi]\b", r"\bscart[oi]\b", r"\bdifett[oi]\b",
        r"\banomali[ae]\b", r"\bgestione non conform",
        r"\bnon compliance\b",
    ]),
    ("OPM", [
        r"\boperation management\b", r"\bopm\b",
        r"\bgestione acquist[oi]\b", r"\bricevimento merc[ei]\b",
        r"\bgestione operazion", r"\boperation[is]\b",
    ]),
    ("POR", [
        r"\bporting\b", r"\bmigrazione\b", r"\bupgrade\b",
        r"\baggiornamento version[ei]\b", r"\bnuova version[ei]\b",
        r"\bporting di version[ei]\b",
    ]),
    ("QLT", [
        r"\bgestione qualit[aà]\b", r"\bquality management\b",
        r"\bspc\b", r"\bstatistical process control\b",
        r"\bpiano di controllo\b", r"\baudit\b",
        r"\bcollaud[oi]\b", r"\bcertificazione\b",
        r"\bcontrollo qualit[aà]\b",
    ]),
    ("REP", [
        r"\breportistica\b", r"\bstampe\b", r"\bjasper\b",
        r"\bcrystal report\b", r"\bmodulo di stampa\b",
        r"\btemplate stampa\b", r"\breport\b",
    ]),
    ("SCC", [
        r"\bsupply chain\b", r"\bscc\b",
        r"\bcollaborazione fornitor", r"\bapprovvigionamento\b",
        r"\bvendor management\b", r"\bportale fornitor",
    ]),
    ("SEQ", [
        r"\bsequenziatore\b", r"\bsequencing\b",
        r"\bsequenza di produzione\b", r"\bsequenza operazion",
    ]),
    ("SFC", [
        r"\bsmart factory\b", r"\bsfc\b",
        r"\bsmart factory console\b", r"\bconsole di fabbrica\b",
    ]),
    ("SI", [
        r"\bstandard interface\b",
    ]),
    ("SQL", [
        r"\bquery sql\b", r"\bstored procedure\b",
        r"\btrigger\b", r"\bvista sql\b", r"\bsql server\b",
    ]),
    ("SYS", [
        r"\bsistemistic[ao]\b", r"\binstallazione\b",
        r"\bconfigurazione server\b", r"\binfrastruttura\b",
        r"\bhardware\b", r"\bsoftware di base\b",
        r"\bsystem administration\b",
    ]),
    ("WMS", [
        r"\bwms\b", r"\bwarehouse management\b",
        r"\bgestione magazzino\b", r"\bpicking\b",
        r"\bstoccaggio\b", r"\bubicazion[ei]\b",
        r"\blogistica di magazzino\b",
    ]),
]

# Regole Tipo Documento basate sul nome file
TIPO_DOC_FILENAME_RULES: list[tuple[str, str]] = [
    (r"\btobe\b|\bto[_-]be\b", "TB"),
    (r"\bgap[_\s-]?analysis\b", "GA"),
    (r"\bmanuale\b|\bmanual\b", "MU"),
    (r"\bspecific[ah]\b", "SC"),
    (r"\bdelivery\b", "SC"),
]


def auto_tag_from_path(percorso_relativo: str) -> dict[str, Any]:
    """Suggerisce tag FIP e Area in base al percorso delle cartelle.

    Args:
        percorso_relativo: Il percorso relativo del file.

    Returns:
        Dizionario con i tag suggeriti.
    """
    result: dict[str, Any] = {"fip_suggeriti": [], "aree_suggerite": []}

    # Normalizza il percorso
    path_parts = percorso_relativo.replace("\\", "/").split("/")

    for part in path_parts:
        # Normalizza separatori per word boundary corretto
        part_lower = re.sub(r"[_\-.]", " ", part.lower())

        # FIP da cartella
        for pattern, fip_code in FIP_FOLDER_RULES:
            if re.search(pattern, part_lower):
                if fip_code not in result["fip_suggeriti"]:
                    result["fip_suggeriti"].append(fip_code)

        # Area da cartella
        for pattern, areas in AREA_PATH_RULES:
            if re.search(pattern, part_lower):
                for area in areas:
                    if area not in result["aree_suggerite"]:
                        result["aree_suggerite"].append(area)

    return result


def auto_tag_from_filename(filename: str) -> dict[str, Any]:
    """Suggerisce Area e Tipo Documento in base al nome del file.

    Args:
        filename: Nome del file (senza percorso).

    Returns:
        Dizionario con le classificazioni suggerite.
    """
    result: dict[str, Any] = {
        "aree_suggerite": [],
        "tipo_doc_suggerito": None,
    }

    # Normalizza: sostituisci separatori comuni con spazi per word boundary corretto
    name_lower = re.sub(r"[_\-./\\]", " ", filename.lower())

    # Cerca aree
    for pattern, areas in AREA_FILENAME_RULES:
        if re.search(pattern, name_lower):
            for area in areas:
                if area not in result["aree_suggerite"]:
                    result["aree_suggerite"].append(area)

    # Cerca tipo documento
    for pattern, tipo in TIPO_DOC_FILENAME_RULES:
        if re.search(pattern, name_lower):
            result["tipo_doc_suggerito"] = tipo
            break

    return result


def auto_tag_from_content(
    testo_contenuto: str | None = None,
    titoli_estratti: str | None = None,
    indice_contenuti: str | None = None,
    documento_titolo: str | None = None,
    documento_parole_chiave: str | None = None,
    sommario_estratto: str | None = None,
) -> dict[str, Any]:
    """Suggerisce Area in base al contenuto del documento.

    Cerca le parole chiave di ogni area nel testo, titoli, indice,
    parole chiave e sommario del documento.

    Returns:
        Dizionario con le aree suggerite e i rispettivi match count.
    """
    result: dict[str, Any] = {"aree_suggerite": [], "aree_scores": {}}

    # Combina tutti i testi disponibili, dando peso diverso
    # Titolo e parole chiave valgono di più perché più specifici
    weighted_texts: list[tuple[str, int]] = []
    if documento_titolo:
        weighted_texts.append((documento_titolo.lower(), 3))
    if documento_parole_chiave:
        weighted_texts.append((documento_parole_chiave.lower(), 3))
    if titoli_estratti:
        weighted_texts.append((titoli_estratti.lower(), 2))
    if indice_contenuti:
        weighted_texts.append((indice_contenuti.lower(), 2))
    if sommario_estratto:
        weighted_texts.append((sommario_estratto.lower(), 2))
    if testo_contenuto:
        # Limita il testo analizzato per performance (primi 50k caratteri)
        weighted_texts.append((testo_contenuto[:50000].lower(), 1))

    if not weighted_texts:
        return result

    # Cerca keyword per ogni area
    area_scores: dict[str, int] = {}
    for area_code, keywords in AREA_CONTENT_KEYWORDS:
        score = 0
        for text, weight in weighted_texts:
            for kw_pattern in keywords:
                matches = re.findall(kw_pattern, text)
                score += len(matches) * weight
        if score > 0:
            area_scores[area_code] = score

    if not area_scores:
        return result

    # Ordina per score decrescente e prendi le aree con punteggio significativo
    sorted_areas = sorted(area_scores.items(), key=lambda x: -x[1])
    top_score = sorted_areas[0][1]

    for area_code, score in sorted_areas:
        # Includi aree con punteggio >= 30% del top score (per non escludere aree rilevanti)
        if score >= top_score * 0.3:
            result["aree_suggerite"].append(area_code)

    result["aree_scores"] = area_scores
    return result


def merge_auto_tags(
    path_tags: dict[str, Any],
    filename_tags: dict[str, Any],
    content_tags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Unisce i tag da percorso, nome file e contenuto in un unico risultato.

    La priorità è: filename > path > content (il contenuto conferma/aggiunge).
    """
    aree: list[str] = []

    # Prima le aree da filename (più precise)
    for a in filename_tags.get("aree_suggerite", []):
        if a not in aree:
            aree.append(a)

    # Poi le aree da path
    for a in path_tags.get("aree_suggerite", []):
        if a not in aree:
            aree.append(a)

    # Infine le aree da contenuto
    if content_tags:
        for a in content_tags.get("aree_suggerite", []):
            if a not in aree:
                aree.append(a)

    return {
        "fip_suggeriti": path_tags.get("fip_suggeriti", []),
        "aree_suggerite": aree,
        "aree_scores": content_tags.get("aree_scores", {}) if content_tags else {},
        "tipo_doc_suggerito": filename_tags.get("tipo_doc_suggerito"),
    }
