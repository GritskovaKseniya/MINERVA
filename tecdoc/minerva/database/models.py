"""Definizione dello schema database SQLite per Minerva."""

SCHEMA_SQL = """
-- Tabella stati documento (lookup)
CREATE TABLE IF NOT EXISTS stato_documento (
    stato_codice       TEXT PRIMARY KEY,
    stato_descrizione  TEXT NOT NULL
);

-- Tabella settori produttivi
CREATE TABLE IF NOT EXISTS settore (
    id_settore         INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_settore        TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);

-- Tabella clienti
CREATE TABLE IF NOT EXISTS cliente (
    cliente_cartella   TEXT PRIMARY KEY,
    bus_part_tipo      TEXT,
    bus_part_codice    TEXT,
    id_settore         INTEGER,
    note               TEXT,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT,
    FOREIGN KEY (id_settore) REFERENCES settore(id_settore)
);

CREATE INDEX IF NOT EXISTS idx_cliente_settore ON cliente(id_settore);

-- Tabella aree principali
CREATE TABLE IF NOT EXISTS area (
    id_area            INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_area           TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);

-- Tabella sotto-aree
CREATE TABLE IF NOT EXISTS sotto_area (
    id_sotto_area      INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_sotto_area     TEXT NOT NULL,
    id_area            INTEGER NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT,
    UNIQUE (cod_sotto_area, id_area),
    FOREIGN KEY (id_area) REFERENCES area(id_area) ON DELETE CASCADE
);

-- Tabella sub-aree
CREATE TABLE IF NOT EXISTS sub_area (
    id_sub_area        INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_sub_area       TEXT NOT NULL,
    id_sotto_area      INTEGER NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT,
    UNIQUE (cod_sub_area, id_sotto_area),
    FOREIGN KEY (id_sotto_area) REFERENCES sotto_area(id_sotto_area) ON DELETE CASCADE
);

-- Tabella tipi documento
CREATE TABLE IF NOT EXISTS tipo_documento (
    id_tipo_documento  INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_tipo_documento TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);

-- Tabella FIP
CREATE TABLE IF NOT EXISTS fip (
    id_fip             INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_fip            TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1
);

-- Tabella documenti (principale)
CREATE TABLE IF NOT EXISTS documenti (
    id_documento                INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_cartella            TEXT NOT NULL,
    bus_part_tipo               TEXT,
    bus_part_codice             TEXT,
    percorso_base               TEXT NOT NULL,
    percorso_relativo           TEXT NOT NULL UNIQUE,
    documento_nome_file         TEXT NOT NULL,
    documento_titolo            TEXT,
    documento_revisione         TEXT,
    documento_revisione_data    TEXT,
    documento_data_creazione    TEXT,
    documento_data_ultima_modifica TEXT,
    documento_dimensione        INTEGER,
    documento_estensione        TEXT,
    documento_hash              TEXT,
    stato                       TEXT NOT NULL DEFAULT 'NEW',
    classificazione             TEXT NOT NULL DEFAULT 'Non Classificato',
    attivo                      INTEGER NOT NULL DEFAULT 0,
    descrizione                 TEXT,
    autore                      TEXT,
    autore_ultima_modifica      TEXT,
    versione_interna            TEXT,
    progetto                    TEXT,
    documento_parole_chiave     TEXT,
    fip                         TEXT,
    titoli_estratti             TEXT,
    indice_contenuti            TEXT,
    sommario_estratto           TEXT,
    metadati_json               TEXT,
    id_documento_principale     INTEGER,
    inserimento_data            TEXT DEFAULT (datetime('now','localtime')),
    inserimento_utente          TEXT,
    ultima_modifica_data        TEXT,
    ultima_modifica_utente      TEXT,
    ultimo_censimento_data      TEXT,
    ultimo_censimento_utente    TEXT,
    FOREIGN KEY (stato) REFERENCES stato_documento(stato_codice),
    FOREIGN KEY (id_documento_principale) REFERENCES documenti(id_documento),
    FOREIGN KEY (cliente_cartella) REFERENCES cliente(cliente_cartella)
);

CREATE INDEX IF NOT EXISTS idx_documenti_cliente ON documenti(cliente_cartella);
CREATE INDEX IF NOT EXISTS idx_documenti_stato ON documenti(stato);
CREATE INDEX IF NOT EXISTS idx_documenti_hash ON documenti(documento_hash);
CREATE INDEX IF NOT EXISTS idx_documenti_nome_file ON documenti(documento_nome_file);
CREATE INDEX IF NOT EXISTS idx_documenti_classificazione ON documenti(classificazione);
CREATE INDEX IF NOT EXISTS idx_documenti_estensione ON documenti(documento_estensione);
CREATE INDEX IF NOT EXISTS idx_documenti_principale ON documenti(id_documento_principale);

-- Tabella relazione M2M documenti-classificazioni
CREATE TABLE IF NOT EXISTS documento_classificazione (
    id_documento       INTEGER NOT NULL,
    id_area            INTEGER NOT NULL,
    id_sotto_area      INTEGER,
    id_sub_area        INTEGER,
    PRIMARY KEY (id_documento, id_area),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_area) REFERENCES area(id_area),
    FOREIGN KEY (id_sotto_area) REFERENCES sotto_area(id_sotto_area),
    FOREIGN KEY (id_sub_area) REFERENCES sub_area(id_sub_area)
);

-- Tabella relazione M2M documenti-tipi
CREATE TABLE IF NOT EXISTS documento_tipo (
    id_documento       INTEGER NOT NULL,
    id_tipo_documento  INTEGER NOT NULL,
    PRIMARY KEY (id_documento, id_tipo_documento),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_documento) REFERENCES tipo_documento(id_tipo_documento)
);

-- Tabella relazione M2M documenti-FIP
CREATE TABLE IF NOT EXISTS documento_fip (
    id_documento       INTEGER NOT NULL,
    id_fip             INTEGER NOT NULL,
    PRIMARY KEY (id_documento, id_fip),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_fip) REFERENCES fip(id_fip)
);
"""

# FTS5 va creata separatamente perché executescript non supporta bene le virtual table
FTS_SCHEMA_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS documenti_fts USING fts5(
    documento_nome_file,
    documento_titolo,
    testo_contenuto,
    documento_parole_chiave,
    titoli_estratti,
    indice_contenuti,
    sommario_estratto,
    tokenize='unicode61 remove_diacritics 2'
);
"""

# Dati iniziali per il seed del database
SEED_DATA = {
    "stato_documento": [
        ("NEW", "Nuovo: È stato aggiunto un nuovo file che non esisteva prima"),
        ("ESU", "Esistente Unico: Il file è presente e non è stato duplicato né modificato"),
        ("MOD", "Modificato: Il file è stato modificato rispetto all'ultima scansione"),
        ("CAN", "Cancellato: Il file non esiste più in alcun percorso"),
        ("SPO", "Spostato: Il file è stato trovato in un nuovo percorso"),
        ("DUP", "Duplicato: Il file è presente in più percorsi"),
        ("EXD", "Esistente con Duplicati: Il file esiste ancora e ha duplicati in altri percorsi"),
    ],
    "area": [
        ("ALL", "All Topics - Jolly che include tutti gli argomenti"),
        ("APS", "Advanced Planning and Scheduling"),
        ("BI", "Business Intelligence"),
        ("FLEX3", "Integrazione con Flex3"),
        ("IND", "Industry - Interconnessioni Macchine, Industry 4.0 e 5.0"),
        ("INT", "Integrazione - Integrazioni con Sistemi Gestionali e Altri Sistemi Informativi Aziendali"),
        ("JAD", "Jflex Advanced Dashboard - Cruscotti"),
        ("KPI", "Rendicontazione e Reportistica ed Analisi KPI"),
        ("MAN", "Manutenzione"),
        ("MCS", "Manufacturing Control System"),
        ("MES", "MES & MOM - Manufacturing Execution System / Manufacturing Operations Management"),
        ("NC", "Non Conformità"),
        ("OPM", "Operation Management"),
        ("POR", "Porting di versione"),
        ("QLT", "Gestione Qualità"),
        ("REP", "Reportistica/Stampe"),
        ("SCC", "Supply Chain Collaboration"),
        ("SEQ", "Sequenziatore"),
        ("SFC", "Smart Factory Console"),
        ("SI", "Standard Interface"),
        ("SQL", "Query SQL"),
        ("SYS", "Attività Sistemistica HW/SW"),
        ("VAR", "Varie"),
        ("WMS", "Warehouse Management System"),
    ],
    "sotto_area_mes": [
        ("PRMG", "Process Management - Gestione dei processi"),
        ("DPUN", "Dispatching Production Unit - Dispatch unità di produzione"),
        ("LMGT", "Labor Management - Gestione risorse umane"),
        ("DCOL", "Data Collection & Acquisition - Raccolta e acquisizione dati"),
        ("CTRL", "Controls: PLC, TLC, others"),
        ("QUAL", "Quality Management - Gestione qualità"),
        ("TRAC", "Product Tracking & Genealogy - Tracciabilità e genealogia"),
        ("RALL", "Resource Allocation & Status"),
        ("LOGS", "Logistics focused: WMS, TMS"),
        ("PANA", "Performance Analysis - Analisi prestazioni"),
        ("MULT", "Multiple Topics - Jolly multi-argomento"),
    ],
    "sub_area_aps": [
        ("DPLN", "Pianificazione della domanda (Demand Planning)"),
        ("PPRD", "Pianificazione della produzione (Production Planning)"),
        ("OSCH", "Schedulazione delle operazioni (Operations Scheduling)"),
        ("RMGT", "Gestione delle risorse (Resource Management)"),
        ("COPT", "Ottimizzazione dei vincoli (Constraints Optimization)"),
        ("WISC", "Simulazione di scenari (What-if Scenarios)"),
        ("RTMA", "Monitoraggio e aggiornamento in tempo reale"),
        ("MULT", "Multiple Topics"),
    ],
    "sub_area_qual": [
        ("MULT", "Multiple Topics"),
        ("PCNT", "Piani di controllo"),
        ("BMSC", "Configurazione anagrafiche di base"),
        ("TQMG", "Total Quality Management"),
        ("DFDT", "Rilevazione difetti"),
        ("SAMP", "Campionamenti"),
        ("NCMT", "Gestione non conformità"),
        ("INAD", "Audit interni di qualità"),
        ("CERT", "Certificazioni di prodotto"),
        ("SPCA", "Analisi statistica del processo (SPC)"),
    ],
    "settore": [
        ("ALIM", "Alimentare e Bevande"),
        ("AUTO", "Automotive e Mezzi di Trasporto"),
        ("CARP", "Carpenteria e Lavorazioni Meccaniche"),
        ("CART", "Carta"),
        ("CERA", "Ceramica"),
        ("CHIM", "Chimica-Farmaceutico"),
        ("COMM", "Commercio"),
        ("OLEM", "Componenti Oleodinamici e Motoriduttori"),
        ("REFR", "Componenti Refrigerazione Riscaldamento"),
        ("COSM", "Cosmetico"),
        ("EDIL", "Edilizia"),
        ("EDIT", "Editoria"),
        ("ELET", "Elettrodomestici"),
        ("ELEC", "Elettromeccanica"),
        ("ELTR", "Elettronica"),
        ("FASH", "Fashion/Accessori"),
        ("GOMM", "Gomma"),
        ("IMPI", "Impianti"),
        ("LAMT", "Lavorazione Lamiere/Trafileria"),
        ("LEGN", "Legno Arredo"),
        ("MACC", "Macchine e Apparecchi Meccanici o Elettrici"),
        ("METL", "Metalmeccanico"),
        ("NONA", "Non Assegnato"),
        ("PLAS", "Plastica"),
        ("SANI", "Sanità"),
        ("SERV", "Servizi"),
        ("SIDE", "Siderurgia Fonderia Stampaggio"),
        ("TESS", "Tessile"),
        ("VETR", "Vetro"),
        ("ALTR", "Altra Industria Manifatturiera"),
    ],
    "tipo_documento": [
        ("SC", "Specifica Software Custom per Cliente"),
        ("SS", "Specifica Software Standard"),
        ("TS", "Test Software"),
        ("MU", "Manuale Utente"),
        ("CU", "Casi d'Uso"),
        ("NU", "Note per l'Utente"),
        ("GA", "Gap Analysis"),
        ("AV", "Avanzamento Progetto"),
        ("SV", "Specifica per lo Sviluppo"),
        ("TB", "Modello To Be"),
        ("CR", "Change Request"),
        ("AP", "Appunti"),
        ("MN", "Minute Incontri"),
        ("MT", "Multiple Topics"),
    ],
    "fip": [
        ("PRJM", "Project Management - Pianificazione, coordinamento e supervisione attività"),
        ("ENGR", "Engineering - Progettazione e sviluppo sistemi e soluzioni tecniche"),
        ("VISN", "Visioning - Definizione visione e direzione strategica"),
        ("PILT", "Piloting - Test e implementazione iniziale su scala ridotta"),
        ("TEST", "Testing - Controllo e verifica funzionalità"),
        ("TRNG", "Training - Formazione utenti finali"),
        ("TUNG", "Tuning - Ottimizzazione sistema"),
        ("SUPP", "Supporting - Assistenza continua e manutenzione"),
    ],
}
