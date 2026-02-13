"""Gestione configurazione globale Minerva."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_FILE = "minerva_config.json"


@dataclass
class DatabaseConfig:
    path: str = "./data/minerva.db"
    backup_enabled: bool = True
    backup_path: str = "./data/backups/"


@dataclass
class PercorsoBase:
    nome: str
    percorso: str
    tipo: str  # "clienti" o "fip"


@dataclass
class FiltroData:
    usa_giorni_all_indietro: bool = False
    giorni_all_indietro: int | None = None
    data_inizio: str | None = None
    data_fine: str | None = None


@dataclass
class FiltroGlobaleDefault:
    formati_da_leggere: list[str] = field(
        default_factory=lambda: ["*.docx", "*.doc", "*.pdf", "*.xlsx", "*.xls", "*.txt", "*.xml", "*.sql", "*.cmd", "*.ksh", "*.eml", "*.ppt", "*.pptx", "*.mpp"]
    )
    filtro_data: FiltroData = field(default_factory=FiltroData)


DEFAULT_FILE_ESCLUSI_REGEX: list[str] = [
    r"^~",              # File temporanei Word/Excel (~$documento.docx, ~WRL1234.tmp)
    r"^\.",             # File nascosti/dotfiles (.DS_Store, .gitignore, ._resource)
    r"^Thumbs\.db$",   # Cache miniature Windows
    r"^desktop\.ini$",  # Configurazione cartelle Windows
    r"^ehthumbs\.db$",  # Cache miniature Windows (vecchio)
    r"\.tmp$",          # File temporanei generici
    r"\.bak$",          # File di backup generici
    r"\.lnk$",          # Collegamento Windows
]


@dataclass
class ScannerConfig:
    filtro_globale_default: FiltroGlobaleDefault = field(
        default_factory=FiltroGlobaleDefault
    )
    hash_algorithm: str = "sha256"
    max_file_size_mb: int = 100
    utente_scanner: str = "MINERVA_SCANNER"
    file_esclusi_regex: list[str] = field(
        default_factory=lambda: list(DEFAULT_FILE_ESCLUSI_REGEX)
    )


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    timeout_seconds: int = 120
    max_retries: int = 3
    max_text_chars: int = 100000
    enabled: bool = True


@dataclass
class AreaDef:
    """Definizione di un'area di classificazione."""
    codice: str
    descrizione: str


@dataclass
class ClassificazioneConfig:
    """Configurazione delle tabelle di classificazione (lookup)."""
    aree: list[AreaDef] = field(default_factory=list)


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    results_per_page: int = 50


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "./logs/minerva.log"
    max_size_mb: int = 50
    backup_count: int = 5
    retention_hours: int = 24


@dataclass
class MinervaConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    percorsi_base: list[PercorsoBase] = field(default_factory=list)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    classificazione: ClassificazioneConfig = field(default_factory=ClassificazioneConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    web: WebConfig = field(default_factory=WebConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _parse_filtro_data(data: dict[str, Any]) -> FiltroData:
    return FiltroData(
        usa_giorni_all_indietro=data.get("usa_giorni_all_indietro", False),
        giorni_all_indietro=data.get("giorni_all_indietro"),
        data_inizio=data.get("data_inizio"),
        data_fine=data.get("data_fine"),
    )


def load_config(config_path: str | Path | None = None) -> MinervaConfig:
    """Carica la configurazione dal file JSON."""
    if config_path is None:
        config_path = Path(CONFIG_FILE)
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        logger.warning("File di configurazione %s non trovato, uso default", config_path)
        return MinervaConfig()

    with open(config_path, encoding="utf-8") as f:
        raw = json.load(f)

    db_raw = raw.get("database", {})
    database = DatabaseConfig(
        path=db_raw.get("path", "./data/minerva.db"),
        backup_enabled=db_raw.get("backup_enabled", True),
        backup_path=db_raw.get("backup_path", "./data/backups/"),
    )

    percorsi_base = [
        PercorsoBase(nome=p["nome"], percorso=p["percorso"], tipo=p["tipo"])
        for p in raw.get("percorsi_base", [])
    ]

    sc_raw = raw.get("scanner", {})
    fg_raw = sc_raw.get("filtro_globale_default", {})
    filtro_globale = FiltroGlobaleDefault(
        formati_da_leggere=fg_raw.get(
            "formati_da_leggere", ["*.docx", "*.doc", "*.pdf", "*.xlsx", "*.xls", "*.txt", "*.xml", "*.sql", "*.cmd", "*.ksh", "*.eml", "*.ppt", "*.pptx", "*.mpp"]
        ),
        filtro_data=_parse_filtro_data(fg_raw.get("filtro_data", {})),
    )
    scanner = ScannerConfig(
        filtro_globale_default=filtro_globale,
        hash_algorithm=sc_raw.get("hash_algorithm", "sha256"),
        max_file_size_mb=sc_raw.get("max_file_size_mb", 100),
        utente_scanner=sc_raw.get("utente_scanner", "MINERVA_SCANNER"),
        file_esclusi_regex=sc_raw.get("file_esclusi_regex", list(DEFAULT_FILE_ESCLUSI_REGEX)),
    )

    cl_raw = raw.get("classificazione", {})
    classificazione = ClassificazioneConfig(
        aree=[
            AreaDef(codice=a["codice"], descrizione=a["descrizione"])
            for a in cl_raw.get("aree", [])
        ],
    )

    ol_raw = raw.get("ollama", {})
    ollama = OllamaConfig(
        base_url=ol_raw.get("base_url", "http://localhost:11434"),
        model=ol_raw.get("model", "llama3"),
        timeout_seconds=ol_raw.get("timeout_seconds", 120),
        max_retries=ol_raw.get("max_retries", 3),
        max_text_chars=ol_raw.get("max_text_chars", 100000),
        enabled=ol_raw.get("enabled", True),
    )

    web_raw = raw.get("web", {})
    web = WebConfig(
        host=web_raw.get("host", "0.0.0.0"),
        port=web_raw.get("port", 5000),
        debug=web_raw.get("debug", False),
        results_per_page=web_raw.get("results_per_page", 50),
    )

    log_raw = raw.get("logging", {})
    logging_cfg = LoggingConfig(
        level=log_raw.get("level", "INFO"),
        file=log_raw.get("file", "./logs/minerva.log"),
        max_size_mb=log_raw.get("max_size_mb", 50),
        backup_count=log_raw.get("backup_count", 5),
        retention_hours=log_raw.get("retention_hours", 24),
    )

    return MinervaConfig(
        database=database,
        percorsi_base=percorsi_base,
        scanner=scanner,
        classificazione=classificazione,
        ollama=ollama,
        web=web,
        logging=logging_cfg,
    )


def load_censimento_filtro(client_path: Path, global_defaults: FiltroGlobaleDefault) -> dict[str, Any] | None:
    """Carica il file censimento_filtro.json per un cliente.

    Merge con i default globali: i campi presenti nel file locale
    sovrascrivono i default, quelli assenti ereditano il valore globale.
    Restituisce None se il file non esiste (il cliente viene saltato).
    """
    filtro_path = client_path / "censimento_filtro.json"
    if not filtro_path.exists():
        return None

    with open(filtro_path, encoding="utf-8") as f:
        raw = json.load(f)

    filtro = raw.get("censimento_filtro", {})

    # Merge con default globali
    result: dict[str, Any] = {
        "directory_da_leggere": filtro.get("directory_da_leggere", ["/*"]),
        "directory_da_evitare": filtro.get("directory_da_evitare", []),
        "formati_da_leggere": filtro.get(
            "formati_da_leggere", global_defaults.formati_da_leggere
        ),
    }

    # Merge filtro_data
    fd_raw = filtro.get("filtro_data", {})
    gd = global_defaults.filtro_data
    result["filtro_data"] = FiltroData(
        usa_giorni_all_indietro=fd_raw.get(
            "usa_giorni_all_indietro", gd.usa_giorni_all_indietro
        ),
        giorni_all_indietro=fd_raw.get("giorni_all_indietro", gd.giorni_all_indietro),
        data_inizio=fd_raw.get("data_inizio", gd.data_inizio),
        data_fine=fd_raw.get("data_fine", gd.data_fine),
    )

    return result
