# MINERVA - Classificatore Documenti

## Product Requirements Document (PRD) di Dettaglio

**Versione:** 1.0
**Data:** 08/02/2026
**Progetto:** GPT & Friends - Minerva
**Basato su:** GPT&Friends.Minerva.ClassificatoreDocumenti.SpecificheTecniche.R00.docx

---

## INDICE

1. [Contesto e Obiettivi](#1-contesto-e-obiettivi)
2. [Architettura del Sistema](#2-architettura-del-sistema)
3. [Componente 1: Scanner / Analizzatore Documenti](#3-componente-1-scanner--analizzatore-documenti)
4. [Componente 2: Interfaccia Web di Ricerca e Gestione](#4-componente-2-interfaccia-web-di-ricerca-e-gestione)
5. [Schema Database SQLite](#5-schema-database-sqlite)
6. [Configurazione](#6-configurazione)
7. [Integrazione AI (Ollama)](#7-integrazione-ai-ollama)
8. [Gestione Revisioni](#8-gestione-revisioni)
9. [Sistema di Classificazione e Tag](#9-sistema-di-classificazione-e-tag)
10. [Gestione Stati Documento](#10-gestione-stati-documento)
11. [Requisiti Non Funzionali](#11-requisiti-non-funzionali)
12. [Piano di Verifica e Test](#12-piano-di-verifica-e-test)
13. [Appendici](#13-appendici)

---

## 1. Contesto e Obiettivi

### 1.1 Contesto Aziendale

Tecnest gestisce un patrimonio documentale di oltre **215.000 file** distribuiti in circa **44.000 cartelle** sulla rete aziendale. Questa documentazione, accumulata nel tempo con convenzioni di nomenclatura eterogenee, risulta difficilmente navigabile e non catalogata.

Il software Minerva nasce come strumento di **analisi, classificazione e catalogazione** dei documenti esistenti, basandosi sulle informazioni contenute nel filesystem. Il progetto si colloca nel contesto dell'iniziativa "Pillole di A.I. in Tecnest" (GPT & Friends) e rappresenta il primo passo verso una gestione documentale evoluta, con possibile futura integrazione con Microsoft 365 / Microsoft Syntex e tecnologie di AI generativa.

### 1.2 Obiettivi Principali

| # | Obiettivo | Descrizione |
|---|---|---|
| 1 | **Censimento automatico** | Scansione periodica delle directory configurate per individuare, catalogare e tracciare tutti i documenti presenti |
| 2 | **Classificazione assistita** | Pre-classificazione automatica tramite analisi del nome file, percorso, metadati interni e contenuto (via Ollama AI locale), con successivo completamento manuale |
| 3 | **Ricerca e consultazione** | Interfaccia web per la ricerca, il filtraggio e la consultazione rapida della base documentale |
| 4 | **Tracciamento revisioni** | Riconoscimento automatico di file che rappresentano revisioni successive dello stesso documento (pattern `.R00`, `.R01`, ecc.) |
| 5 | **Tracciamento stato** | Monitoraggio continuo dello stato di ciascun file (nuovo, modificato, spostato, cancellato, duplicato, ecc.) |

### 1.3 Stack Tecnologico

| Componente | Tecnologia | Motivazione |
|---|---|---|
| Linguaggio | **Python 3.10+** | Backend e scanner |
| Database | **SQLite** | Leggero, zero-config, file-based. Adattato da Oracle (spec originale) |
| AI Locale | **Ollama** | Estrazione metadati, keyword, classificazione senza dipendenze cloud |
| Web UI | **Flask** (o Streamlit) | Interfaccia web interna aziendale |
| Scheduling | Cron / Task Scheduler / APScheduler | Esecuzione periodica dello scanner |

### 1.4 Utenti Target

- **Capocommessa**: Responsabile della classificazione manuale dei documenti dei propri clienti
- **Personale tecnico**: Consulta la base documentale per ricerche operative (specifiche, manuali, gap analysis)
- **Direzione / PM**: Visione d'insieme dello stato documentale per cliente e progetto
- **Sistema automatico**: Processo di scansione ciclico (notturno o settimanale)

---

## 2. Architettura del Sistema

### 2.1 Panoramica Architetturale

Il sistema si compone di **due macro-componenti** indipendenti che condividono lo stesso database SQLite:

```
+-----------------------------------+       +-----------------------------------+
|  COMPONENTE 1                     |       |  COMPONENTE 2                     |
|  Scanner / Analizzatore           |       |  Interfaccia Web                  |
|  (Processo batch schedulato)      |       |  (Flask / Streamlit)              |
|                                   |       |                                   |
|  - Lettura filesystem             |       |  - Navigazione per cliente        |
|  - Parsing documenti              |       |  - Ricerca full-text e per tag    |
|  - Estrazione metadati            |       |  - Filtro per directory (tree)    |
|  - Classificazione AI (Ollama)    |       |  - Modifica classificazioni       |
|  - Rilevamento revisioni          |       |  - Apertura file / directory      |
|  - Aggiornamento stati            |       |  - Gestione workflow classif.     |
+----------------+------------------+       +----------------+------------------+
                 |                                           |
                 +-------------------------------------------+
                                     |
                          +----------+----------+
                          |    SQLite Database   |
                          |    minerva.db        |
                          +---------------------+
                                     |
                          +----------+----------+
                          |   Ollama (locale)    |
                          |   API REST           |
                          +---------------------+
```

### 2.2 Struttura dei Moduli Python

```
minerva/
  config/
    settings.py                  # Configurazione globale (percorsi base, scheduling, DB)
    censimento_filtro_schema.py  # Schema e validazione JSON filtro
  scanner/
    __init__.py
    directory_walker.py          # Lettura filesystem con filtri
    file_hasher.py               # Calcolo hash per rilevamento duplicati/modifiche
    revision_detector.py         # Logica pattern revisioni (.R00, .R01, ...)
    status_tracker.py            # Determinazione stato (NEW, MOD, DUP, CAN, SPO, ...)
    metadata_extractor.py        # Estrazione metadati da docx, pdf, xlsx
    ai_classifier.py             # Integrazione Ollama per classificazione
    auto_tagger.py               # Auto-tagging da nome file e percorso cartella
    scheduler.py                 # Orchestrazione scansione periodica
  database/
    __init__.py
    models.py                    # Definizione tabelle SQLite
    repository.py                # CRUD operazioni su DB
    migrations.py                # Inizializzazione e migrazione schema
  web/
    __init__.py
    app.py                       # Entry point Flask/Streamlit
    routes.py                    # Endpoint / pagine
    templates/                   # Template HTML (se Flask)
    static/                      # CSS, JS
  utils/
    file_utils.py                # Utility path, formati supportati
    logging_config.py            # Configurazione logging
  main_scanner.py                # Entry point processo di scansione
  main_web.py                    # Entry point interfaccia web
```

### 2.3 Gestione dei Percorsi (Chiave Univoca)

Come specificato nel documento originale, la chiave univoca del documento **NON** deve essere il percorso di rete assoluto completo, per garantire flessibilità rispetto a cambiamenti del server di rete.

Strategia adottata:

- **`percorso_base`**: Parte iniziale del percorso dipendente dal server (es. `\\rete-ud-2\tdl\`). Campo accessorio configurabile.
- **`percorso_relativo`**: **Chiave univoca effettiva**. Es. `documents\Cliente\GR Elettronica\200 VISIONING\SpecificheTecniche\GR_ELETTRONICA_TOBE_Modello_MES.R00.docx`

Lo stesso file fisico può apparire in percorsi relativi diversi (duplicazione) e ciascuna occorrenza avrà il proprio record con il proprio `percorso_relativo` univoco.

---

## 3. Componente 1: Scanner / Analizzatore Documenti

### 3.1 Flusso di Esecuzione Principale

```
1. Caricamento configurazione globale (settings.py / minerva_config.json)

2. Per ciascun percorso base configurato:
   2.1 Enumerazione cartelle di primo livello (= clienti)
   2.2 Per ciascuna cartella cliente:
       2.2.1 Ricerca file censimento_filtro.json nella root della cartella cliente
       2.2.2 Se NON trovato → SKIP (nessun file del cliente viene letto)
       2.2.3 Se trovato → parsing del filtro (merge con config globale)
       2.2.4 Costruzione lista file da analizzare in base a:
             - directory_da_leggere (include)
             - directory_da_evitare (exclude)
             - filtro_data (giorni_all_indietro OPPURE data_inizio/data_fine)
             - formati_da_leggere (estensioni file; "*" = tutti)
       2.2.5 Per ciascun file trovato:
             a) Calcolo percorso_relativo (chiave univoca)
             b) Calcolo hash SHA-256 del file
             c) Ricerca nel DB per percorso_relativo:
                - Non trovato → INSERT con stato NEW
                - Trovato → UPDATE con logica di stato (vedi sez. 10)
             d) Estrazione metadati base dal filesystem
             e) Estrazione metadati avanzati dal contenuto (vedi sez. 7)
             f) Pre-classificazione automatica (nome file + percorso + AI)
             g) Rilevamento revisioni (vedi sez. 8)
       2.2.6 Aggiornamento timestamp censimento

3. Rilevamento file cancellati:
   3.1 Per ogni record in DB non trovato nel filesystem → stato CAN

4. Rilevamento file spostati:
   4.1 Confronto hash dei file NEW con hash dei file CAN
   4.2 Se match → il file è stato spostato (stato SPO)

5. Rilevamento duplicati:
   5.1 Raggruppamento record per hash + nome file
   5.2 Se più record con stesso hash e nome:
       - Record originale (più vecchio) → EXD
       - Altri record → DUP

6. Log e report dell'esecuzione
```

### 3.2 Directory Walker - Logica dei Filtri

Il file `censimento_filtro.json` segue questo schema:

```json
{
    "censimento_filtro": {
        "directory_da_leggere": [
            "/*"
        ],
        "directory_da_evitare": [
            "Documenti ricevuti",
            "Dota",
            "Fatturazione",
            "SpecifichePersonalizzazioni/Old&Furious"
        ],
        "filtro_data": {
            "usa_giorni_all_indietro": true,
            "giorni_all_indietro": 30,
            "data_inizio": null,
            "data_fine": null
        },
        "formati_da_leggere": [
            "*.docx", "*.doc", "*.pdf", "*.xlsx", "*.xls"
        ]
    }
}
```

**Regole di filtro:**

| Campo | Descrizione |
|---|---|
| `directory_da_leggere` | Percorsi relativi alla cartella cliente. `"/*"` = tutte le sotto-directory |
| `directory_da_evitare` | Percorsi relativi da escludere. Applicate come esclusione dopo l'inclusione |
| `filtro_data` | Se `usa_giorni_all_indietro=true` → solo file modificati entro N giorni. Se `false` → range `data_inizio`/`data_fine`. Se entrambi null → nessun filtro temporale |
| `formati_da_leggere` | Pattern glob per le estensioni. `["*"]` = tutti i formati |

**Regola fondamentale:** Se il file `censimento_filtro.json` **non è presente** nella cartella di un cliente, quel cliente viene interamente saltato. Meccanismo di opt-in esplicito.

### 3.3 Configurazione Ibrida: Globale + Override Locale

```
1. Config globale (minerva_config.json) ← default per tutti i clienti
     |
     v  (override per singolo campo)
2. censimento_filtro.json per cliente ← sovrascrive i default
     |
     v  (priorità massima)
3. Valori calcolati a runtime (hash, date, metadati)
```

I campi presenti nel `censimento_filtro.json` sovrascrivono i default globali. I campi **assenti** nel filtro locale **ereditano** il valore dalla configurazione globale.

### 3.4 Calcolo Hash

Per ogni file viene calcolato un **hash SHA-256** sul contenuto binario. Questo serve per:

- **Rilevare modifiche**: hash diverso rispetto all'ultimo censimento → stato MOD
- **Rilevare duplicati**: stesso hash + stesso nome file in percorsi diversi → DUP/EXD
- **Rilevare spostamenti**: stesso hash, percorso diverso, vecchio percorso non esiste più → SPO

L'hash viene memorizzato nel campo `documento_hash` della tabella `documenti`.

### 3.5 Estrazione Metadati dal Filesystem

Per ogni file, dal filesystem si estraggono:

| Campo DB | Sorgente |
|---|---|
| `documento_nome_file` | Nome del file senza percorso |
| `percorso_relativo` | Chiave univoca (senza parte server) |
| `percorso_base` | Parte server/share |
| `documento_data_creazione` | Data creazione filesystem |
| `documento_data_ultima_modifica` | Data ultima modifica filesystem |
| `documento_dimensione` | Dimensione in bytes |
| `documento_estensione` | Estensione del file |
| `cliente_cartella` | Nome cartella primo livello (= nome cliente) |

### 3.6 Politica di Non Cancellazione

Il programma **NON cancella mai** record dal database. I record possono essere cancellati solo manualmente dall'utente tramite l'interfaccia web, secondo regole definite. Il processo di scansione esegue **solo INSERT e UPDATE**.

---

## 4. Componente 2: Interfaccia Web di Ricerca e Gestione

### 4.1 Tecnologia

**Flask** come framework web principale. Flask offre maggiore controllo su layout, interattività e personalizzazione della UI rispetto a Streamlit.

### 4.2 Pagina Principale - Lista Documenti

**Layout:**

```
+-----------------------------------------------------------------------+
| [MINERVA - Classificatore Documenti]            [Utente] [Impostazioni] |
+-----------------------------------------------------------------------+
| Pannello Sinistro (sidebar)   | Pannello Centrale                     |
| +--------------------------+  | +-----------------------------------+ |
| | Selezione Cliente        |  | | Barra Filtri Rapidi               | |
| | [Dropdown / Autocomplete]|  | | [Testo libero] [Area ▼] [FIP ▼]  | |
| |                          |  | | [Settore ▼] [Stato ▼] [Classif ▼]| |
| | Struttura Directory      |  | +-----------------------------------+ |
| | [x] 000 PROJECT MGMT    |  | | Tabella Documenti                 | |
| | [x] 100 ENGINEERING     |  | | ID | Nome | Tipo | Area | Stato   | |
| | [ ] 200 VISIONING       |  | | [riga colorata per classif.]      | |
| | [x] 500 TRAINING        |  | | [riga colorata per classif.]      | |
| |   [x] SubDir1           |  | | ...                               | |
| |   [ ] SubDir2           |  | | [Paginazione]                     | |
| +--------------------------+  | +-----------------------------------+ |
+-----------------------------------------------------------------------+
```

**Pannello Sinistro:**
- Dropdown/autocomplete per selezione cliente (basato su `cliente_cartella`)
- **Tree view navigabile** con checkbox per ciascuna directory/sotto-directory censita
- Le checkbox **limitano il perimetro di ricerca**: solo i documenti nelle directory selezionate vengono mostrati

**Barra Filtri:**
- Campo di ricerca **testo libero** (cerca in nome file, titolo, descrizione, parole chiave)
- Dropdown filtro per **Area** (MES, APS, OPM, INT, IND, KPI, ALL)
- Dropdown filtro per **SottoArea** (dinamico in base all'Area selezionata)
- Dropdown filtro per **SubArea** (dinamico in base alla SottoArea selezionata)
- Dropdown filtro per **FIP** (PRJM, ENGR, VISN, PILT, TEST, TRNG, TUNG, SUPP)
- Dropdown filtro per **Settore** (ALIM, AUTO, CARP, ... 24+ settori) - filtra tramite il settore associato al cliente
- Dropdown filtro per **Tipo Documento** (SC, SS, TS, MU, CU, NU, GA, AP, SV, TB, CR, MN, MT)
- Dropdown filtro per **Stato** (ESU, CAN, SPO, DUP, MOD, NEW, EXD)
- Dropdown filtro per **Classificazione** (Non Classificato, Parzialmente Classificato, Classificato)
- Dropdown filtro per **Attivo** (Sì / No)

**Tabella Documenti:**
- Colonne visibili (configurabili): ID, Nome File, Titolo, Area, SottoArea, FIP, Settore, Tipo, Stato, Classificazione, Attivo, Data Ultima Modifica, Revisione
- Ordinamento cliccando sull'intestazione colonna
- Paginazione (25/50/100 risultati per pagina)
- Colorazione righe basata su stato di classificazione

### 4.3 Sistema di Colorazione Righe

| Classificazione | Attivo | Colore Riga |
|---|---|---|
| Non Classificato | No | Testo grigio scuro su sfondo grigio chiaro |
| Non Classificato | Sì | Testo nero su sfondo giallo chiaro |
| Parzialmente Classificato | No | Testo grigio su sfondo giallo pallido |
| Parzialmente Classificato | Sì | Testo nero su sfondo giallo |
| Classificato | No | Testo grigio su sfondo verde pallido |
| Classificato | Sì | Testo nero su sfondo verde chiaro |
| (Qualsiasi) + Stato=CAN | - | Testo rosso barrato su sfondo rosa chiaro |
| (Qualsiasi) + campi obbligatori mancanti | - | Bordo rosso / indicatore di attenzione |

### 4.4 Pagina Dettaglio / Modifica Documento

Cliccando su una riga nella tabella si apre la pagina di dettaglio con le seguenti sezioni:

#### Sezione Informazioni File (sola lettura)
- Percorso completo, nome file, estensione, dimensione
- Date creazione / ultima modifica filesystem
- Hash SHA-256
- Stato (ESU, NEW, MOD, DUP, SPO, CAN, EXD)

#### Sezione Metadati Estratti (sola lettura, compilati dallo scanner)
- Autore (da metadati documento)
- Autore ultima modifica
- Versione interna
- Titoli/sottotitoli estratti
- Parole chiave estratte da AI

#### Sezione Classificazione (modificabile)
- **Classificazione**: dropdown [Non Classificato / Parzialmente Classificato / Classificato]
- **Attivo**: checkbox [Sì / No]
- **Area + SottoArea + SubArea**: interfaccia multi-selezione (un documento può avere N classificazioni)
  - Bottone "Aggiungi classificazione" → riga con 3 dropdown a cascata (Area → SottoArea → SubArea)
  - Possibilità di rimuovere classificazioni esistenti
- **FIP**: dropdown multi-selezione
- **Settore**: dropdown
- **Tipo Documento**: multi-selezione (un documento può avere N tipi)
- **Progetto / Commessa**: campo testo
- **Descrizione**: textarea (fino a 4000 caratteri)
- **Parole chiave manuali**: campo testo / tag input

#### Sezione Revisioni (se presenti)
- Tabella delle revisioni correlate, ordinate per data decrescente
- Indicatore di quale è la revisione "principale" (più recente)
- Link per aprire ciascuna revisione

#### Azioni
- **Salva**: salva le modifiche
- **Apri File**: lancia il file con l'applicazione predefinita
- **Apri Directory**: apre la cartella contenente il file
- **Annulla**: torna alla lista

### 4.5 Regola di Priorità: Classificazione Manuale > Automatica

- I campi compilati manualmente **NON vengono mai sovrascritti** dallo scanner
- Lo scanner aggiorna solo i campi che hanno valore NULL/vuoto nel DB
- Una classificazione manuale ha **SEMPRE priorità** su quella automatica

---

## 5. Schema Database SQLite

### 5.1 Adattamento da Oracle a SQLite

| Oracle | SQLite | Note |
|---|---|---|
| `NUMBER` | `INTEGER` | |
| `VARCHAR2(N)` | `TEXT` | Validazione lunghezza a livello applicativo |
| `DATE DEFAULT SYSDATE` | `TEXT DEFAULT (datetime('now','localtime'))` | Formato ISO 8601 |
| `CLOB` | `TEXT` | |
| Sequence Oracle | `INTEGER PRIMARY KEY AUTOINCREMENT` | |
| `NUMBER(1)` boolean | `INTEGER DEFAULT 1` (0/1) | |
| `CHAR(1) CHECK (IN ('Y','N'))` | `INTEGER DEFAULT 0` (0/1) | |

### 5.2 Tabella `documenti`

```sql
CREATE TABLE documenti (
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

-- Indici per performance
CREATE INDEX idx_documenti_cliente ON documenti(cliente_cartella);
CREATE INDEX idx_documenti_stato ON documenti(stato);
CREATE INDEX idx_documenti_hash ON documenti(documento_hash);
CREATE INDEX idx_documenti_nome_file ON documenti(documento_nome_file);
CREATE INDEX idx_documenti_classificazione ON documenti(classificazione);
CREATE INDEX idx_documenti_estensione ON documenti(documento_estensione);
CREATE INDEX idx_documenti_principale ON documenti(id_documento_principale);
```

**Descrizione campi principali:**

| Campo | Tipo | Descrizione |
|---|---|---|
| `id_documento` | INTEGER PK | Identificativo unico auto-incrementante |
| `cliente_cartella` | TEXT | Nome della cartella cliente (es. "GR Elettronica") |
| `bus_part_tipo` | TEXT | Tipo del partner commerciale |
| `bus_part_codice` | TEXT | Codice del partner commerciale |
| `percorso_base` | TEXT | Parte server/share (es. `\\rete-ud-2\tdl\`) |
| `percorso_relativo` | TEXT UNIQUE | Chiave univoca: percorso relativo + nome file |
| `documento_nome_file` | TEXT | Solo nome file (es. "GR_ELETTRONICA_TOBE.R00.docx") |
| `documento_titolo` | TEXT | Titolo del documento (estratto o manuale) |
| `documento_revisione` | TEXT | Numero revisione (es. "R01") o "OLD" per versioni superate con suffisso .old |
| `documento_revisione_data` | TEXT | Data revisione (ISO 8601) |
| `documento_data_creazione` | TEXT | Data creazione filesystem |
| `documento_data_ultima_modifica` | TEXT | Data ultima modifica filesystem |
| `documento_dimensione` | INTEGER | Dimensione in bytes |
| `documento_estensione` | TEXT | Estensione (es. ".docx") |
| `documento_hash` | TEXT | SHA-256 del contenuto |
| `stato` | TEXT | Codice stato (FK verso stato_documento) |
| `classificazione` | TEXT | Non Classificato / Parzialmente Classificato / Classificato |
| `attivo` | INTEGER | 0=No, 1=Sì |
| `descrizione` | TEXT | Descrizione estesa (max 4000 char a livello app) |
| `autore` | TEXT | Autore/i (es. "Giovanni Rossi, Maria Bianchi") |
| `autore_ultima_modifica` | TEXT | Da metadati documento |
| `versione_interna` | TEXT | Versione interna da metadati |
| `progetto` | TEXT | Identificativo progetto/commessa |
| `documento_parole_chiave` | TEXT | Parole chiave separate da virgola |
| `fip` | TEXT | Codici FIP (gestiti anche via tabella M2M) |
| `titoli_estratti` | TEXT | Titoli/sottotitoli estratti dal documento |
| `sommario_estratto` | TEXT | Sommario/indice estratto |
| `metadati_json` | TEXT | Metadati aggiuntivi in formato JSON |
| `id_documento_principale` | INTEGER | FK self-referencing per catena revisioni |
| `inserimento_data` | TEXT | Data inserimento record nel DB |
| `inserimento_utente` | TEXT | Utente che ha inserito il record |
| `ultima_modifica_data` | TEXT | Data ultima modifica record |
| `ultima_modifica_utente` | TEXT | Utente che ha modificato il record |
| `ultimo_censimento_data` | TEXT | Data dell'ultimo censimento |
| `ultimo_censimento_utente` | TEXT | Utente/processo dell'ultimo censimento |

### 5.3 Tabella `area`

```sql
CREATE TABLE area (
    id_area            INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_area           TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);
```

**Dati iniziali:**

| cod_area | descrizione |
|---|---|
| OPM | Operation Management |
| MES | MES & MOM - Manufacturing Execution System / Manufacturing Operations Management |
| APS | Advanced Planning and Scheduling |
| INT | Integrazione - Integrazioni con Sistemi Gestionali e Altri Sistemi Informativi Aziendali |
| IND | Industry - Interconnessioni Macchine, Industry 4.0 e 5.0 |
| KPI | Rendicontazione e Reportistica ed Analisi KPI |
| ALL | All Topics - Jolly che include tutti gli argomenti |

### 5.4 Tabella `sotto_area`

```sql
CREATE TABLE sotto_area (
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
```

**Dati iniziali per MES:**

| cod_sotto_area | descrizione |
|---|---|
| PRMG | Process Management - Gestione dei processi |
| DPUN | Dispatching Production Unit - Dispatch unità di produzione |
| LMGT | Labor Management - Gestione risorse umane |
| DCOL | Data Collection & Acquisition - Raccolta e acquisizione dati |
| CTRL | Controls: PLC, TLC, others |
| QUAL | Quality Management - Gestione qualità |
| TRAC | Product Tracking & Genealogy - Tracciabilità e genealogia |
| RALL | Resource Allocation & Status |
| LOGS | Logistics focused: WMS, TMS |
| PANA | Performance Analysis - Analisi prestazioni |
| MULT | Multiple Topics - Jolly multi-argomento |

### 5.5 Tabella `sub_area`

```sql
CREATE TABLE sub_area (
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
```

**Dati iniziali per APS (SubAree):**

| cod_sub_area | descrizione |
|---|---|
| DPLN | Pianificazione della domanda (Demand Planning) |
| PPRD | Pianificazione della produzione (Production Planning) |
| OSCH | Schedulazione delle operazioni (Operations Scheduling) |
| RMGT | Gestione delle risorse (Resource Management) |
| COPT | Ottimizzazione dei vincoli (Constraints Optimization) |
| WISC | Simulazione di scenari (What-if Scenarios) |
| RTMA | Monitoraggio e aggiornamento in tempo reale |
| MULT | Multiple Topics |

**Dati iniziali per Qualità (SubAree della SottoArea QUAL):**

| cod_sub_area | descrizione |
|---|---|
| MULT | Multiple Topics |
| PCNT | Piani di controllo |
| BMSC | Configurazione anagrafiche di base |
| TQMG | Total Quality Management |
| DFDT | Rilevazione difetti |
| SAMP | Campionamenti |
| NCMT | Gestione non conformità |
| INAD | Audit interni di qualità |
| CERT | Certificazioni di prodotto |
| SPCA | Analisi statistica del processo (SPC) |

### 5.6 Tabella `documento_classificazione`

```sql
CREATE TABLE documento_classificazione (
    id_documento       INTEGER NOT NULL,
    id_area            INTEGER NOT NULL,
    id_sotto_area      INTEGER,
    id_sub_area        INTEGER,
    PRIMARY KEY (id_documento, id_area, COALESCE(id_sotto_area, 0), COALESCE(id_sub_area, 0)),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_area) REFERENCES area(id_area),
    FOREIGN KEY (id_sotto_area) REFERENCES sotto_area(id_sotto_area),
    FOREIGN KEY (id_sub_area) REFERENCES sub_area(id_sub_area)
);
```

**Nota sulla gestione dei NULL:** I campi `id_sotto_area` e `id_sub_area` possono essere NULL (classificazione parziale a livello superiore). Ogni tabella di classificazione include anche un record "ALL" / "MULT" come jolly esplicito. Questo permette sia la ricerca per livello che l'uso di wildcard.

### 5.7 Relazioni tra le Tabelle di Classificazione

```
area (1) ──────────── (N) sotto_area
sotto_area (1) ──────── (N) sub_area
documenti (M) ──────── (N) classificazioni  (via documento_classificazione)
cliente (1) ──────────── (N) documenti        (via cliente_cartella)
cliente (N) ──────────── (1) settore          (via id_settore)
```

### 5.8 Tabella `cliente`

Il settore è una proprietà del **cliente**, non del singolo documento. La tabella `cliente` associa ogni cartella cliente al proprio settore produttivo.

```sql
CREATE TABLE cliente (
    cliente_cartella   TEXT PRIMARY KEY,           -- Nome cartella (es. "GR Elettronica"), FK da documenti
    bus_part_tipo      TEXT,                        -- Tipo partner commerciale
    bus_part_codice    TEXT,                        -- Codice partner commerciale
    id_settore         INTEGER,                    -- FK verso settore
    note               TEXT,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT,
    FOREIGN KEY (id_settore) REFERENCES settore(id_settore)
);

CREATE INDEX idx_cliente_settore ON cliente(id_settore);
```

**Note:**
- La tabella viene popolata automaticamente dallo scanner quando rileva una nuova cartella di primo livello (= nuovo cliente)
- Il campo `id_settore` viene compilato manualmente dall'utente tramite l'interfaccia web
- Per filtrare i documenti per settore, si esegue una JOIN: `documenti JOIN cliente USING (cliente_cartella) JOIN settore USING (id_settore)`

### 5.9 Tabella `settore`

```sql
CREATE TABLE settore (
    id_settore         INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_settore        TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);
```

**Dati iniziali (24+ settori):**

| cod_settore | descrizione |
|---|---|
| ALIM | Alimentare e Bevande |
| AUTO | Automotive e Mezzi di Trasporto |
| CARP | Carpenteria e Lavorazioni Meccaniche |
| CART | Carta |
| CERA | Ceramica |
| CHIM | Chimica-Farmaceutico |
| COMM | Commercio |
| OLEM | Componenti Oleodinamici e Motoriduttori |
| REFR | Componenti Refrigerazione Riscaldamento |
| COSM | Cosmetico |
| EDIL | Edilizia |
| EDIT | Editoria |
| ELET | Elettrodomestici |
| ELEC | Elettromeccanica |
| ELTR | Elettronica |
| FASH | Fashion/Accessori |
| GOMM | Gomma |
| IMPI | Impianti |
| LAMT | Lavorazione Lamiere/Trafileria |
| LEGN | Legno Arredo |
| MACC | Macchine e Apparecchi Meccanici o Elettrici |
| METL | Metalmeccanico |
| NONA | Non Assegnato |
| PLAS | Plastica |
| SANI | Sanità |
| SERV | Servizi |
| SIDE | Siderurgia Fonderia Stampaggio |
| TESS | Tessile |
| VETR | Vetro |
| ALTR | Altra Industria Manifatturiera |

### 5.10 Tabella `tipo_documento`

```sql
CREATE TABLE tipo_documento (
    id_tipo_documento  INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_tipo_documento TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1,
    data_inserimento   TEXT DEFAULT (datetime('now','localtime')),
    utente_inserimento TEXT,
    data_modifica      TEXT,
    utente_modifica    TEXT
);
```

**Dati iniziali:**

| cod_tipo_documento | descrizione |
|---|---|
| SC | Specifica Software Custom per Cliente |
| SS | Specifica Software Standard |
| TS | Test Software |
| MU | Manuale Utente |
| CU | Casi d'Uso |
| NU | Note per l'Utente |
| GA | Gap Analysis |
| AV | Avanzamento Progetto |
| SV | Specifica per lo Sviluppo |
| TB | Modello To Be |
| CR | Change Request |
| AP | Appunti |
| MN | Minute Incontri |
| MT | Multiple Topics |

### 5.11 Tabella `documento_tipo`

```sql
CREATE TABLE documento_tipo (
    id_documento       INTEGER NOT NULL,
    id_tipo_documento  INTEGER NOT NULL,
    PRIMARY KEY (id_documento, id_tipo_documento),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_tipo_documento) REFERENCES tipo_documento(id_tipo_documento)
);
```

### 5.12 Tabella `stato_documento`

```sql
CREATE TABLE stato_documento (
    stato_codice       TEXT PRIMARY KEY,
    stato_descrizione  TEXT NOT NULL
);

-- Dati iniziali
INSERT INTO stato_documento VALUES ('NEW', 'Nuovo: È stato aggiunto un nuovo file che non esisteva prima');
INSERT INTO stato_documento VALUES ('ESU', 'Esistente Unico: Il file è presente e non è stato duplicato né modificato');
INSERT INTO stato_documento VALUES ('MOD', 'Modificato: Il file è stato modificato rispetto all''ultima scansione');
INSERT INTO stato_documento VALUES ('CAN', 'Cancellato: Il file non esiste più in alcun percorso');
INSERT INTO stato_documento VALUES ('SPO', 'Spostato: Il file è stato trovato in un nuovo percorso');
INSERT INTO stato_documento VALUES ('DUP', 'Duplicato: Il file è presente in più percorsi');
INSERT INTO stato_documento VALUES ('EXD', 'Esistente con Duplicati: Il file esiste ancora e ha duplicati in altri percorsi');
```

### 5.13 Tabelle FIP

```sql
CREATE TABLE fip (
    id_fip             INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_fip            TEXT UNIQUE NOT NULL,
    descrizione        TEXT NOT NULL,
    abilitato          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE documento_fip (
    id_documento       INTEGER NOT NULL,
    id_fip             INTEGER NOT NULL,
    PRIMARY KEY (id_documento, id_fip),
    FOREIGN KEY (id_documento) REFERENCES documenti(id_documento) ON DELETE CASCADE,
    FOREIGN KEY (id_fip) REFERENCES fip(id_fip)
);
```

**Dati iniziali FIP (F = Flex, I = Implementing, P = Project):**

| cod_fip | descrizione |
|---|---|
| PRJM | Project Management - Pianificazione, coordinamento e supervisione attività |
| ENGR | Engineering - Progettazione e sviluppo sistemi e soluzioni tecniche |
| VISN | Visioning - Definizione visione e direzione strategica |
| PILT | Piloting - Test e implementazione iniziale su scala ridotta |
| TEST | Testing - Controllo e verifica funzionalità |
| TRNG | Training - Formazione utenti finali |
| TUNG | Tuning - Ottimizzazione sistema |
| SUPP | Supporting - Assistenza continua e manutenzione |

---

## 6. Configurazione

### 6.1 File di Configurazione Globale

File: `config/minerva_config.json`

```json
{
    "database": {
        "path": "./data/minerva.db",
        "backup_enabled": true,
        "backup_path": "./data/backups/"
    },
    "percorsi_base": [
        {
            "nome": "Tibel",
            "percorso": "C:\\Nextcloud\\LavoroCloud\\Tibel",
            "tipo": "clienti"
        },
        {
            "nome": "Clienti Rete",
            "percorso": "\\\\rete-ud-2\\tdl\\documents\\Cliente",
            "tipo": "clienti"
        },
        {
            "nome": "FIP",
            "percorso": "\\\\rete-ud-2\\TDL\\documents\\Cliente\\_TECNEST_FIP",
            "tipo": "fip"
        }
    ],
    "scanner": {
        "scheduling": {
            "tipo": "cron",
            "cron_expression": "0 2 * * *",
            "nota": "Ogni notte alle 02:00"
        },
        "filtro_globale_default": {
            "formati_da_leggere": ["*.docx", "*.doc", "*.pdf", "*.xlsx", "*.xls"],
            "filtro_data": {
                "usa_giorni_all_indietro": false,
                "giorni_all_indietro": null,
                "data_inizio": null,
                "data_fine": null
            }
        },
        "hash_algorithm": "sha256",
        "max_file_size_mb": 100,
        "utente_scanner": "MINERVA_SCANNER"
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "llama3",
        "timeout_seconds": 120,
        "max_retries": 3,
        "max_text_chars": 100000,
        "enabled": true
    },
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false,
        "results_per_page": 50
    },
    "logging": {
        "level": "INFO",
        "file": "./logs/minerva.log",
        "max_size_mb": 50,
        "backup_count": 5
    }
}
```

### 6.2 File di Filtro Per Cliente

Posizionato nella **root** di ciascuna cartella cliente: `censimento_filtro.json`

Schema già descritto nella sezione 3.2.

### 6.3 Gerarchia di Configurazione

| Priorità | Sorgente | Descrizione |
|---|---|---|
| 1 (bassa) | `minerva_config.json` | Default globali per tutti i clienti |
| 2 (alta) | `censimento_filtro.json` per cliente | Sovrascrive i default globali |
| 3 (max) | Valori runtime | Hash, date, metadati calcolati |

---

## 7. Integrazione AI (Ollama)

### 7.1 Architettura di Integrazione

Lo scanner comunica con Ollama tramite la sua API REST locale (`http://localhost:11434/api/generate` o `/api/chat`). L'integrazione avviene nel modulo `scanner/ai_classifier.py`.

### 7.2 Casi d'Uso dell'AI

#### 7.2.1 Estrazione Parole Chiave e Classificazione

Per ogni documento analizzato, il contenuto (o un estratto: primi N paragrafi, sommario, titoli) viene inviato a Ollama con un prompt strutturato:

```
Sei un assistente specializzato nella classificazione di documenti tecnici aziendali
nel settore manifatturiero (MES, APS, ERP). Analizza il seguente testo estratto da un
documento e restituisci:

1. Una lista di parole chiave rilevanti (max 20)
2. Un breve riassunto del contenuto (max 200 parole)
3. Le aree tematiche probabili tra: OPM, MES, APS, INT, IND, KPI
4. Il tipo documento probabile tra: SC, SS, TS, MU, CU, NU, GA, AV, SV, TB, CR, AP, MN

Testo:
{contenuto_documento}

Rispondi SOLO in formato JSON:
{
    "parole_chiave": [...],
    "riassunto": "...",
    "aree_suggerite": [...],
    "tipo_documento_suggerito": "..."
}
```

#### 7.2.2 Estrazione Metadati da Contenuto

Per documenti dove i metadati standard non sono disponibili (es. PDF senza properties), Ollama può analizzare il testo per estrarre autore probabile, data probabile, tipo documento.

### 7.3 Estrazione Metadati Diretta (senza AI)

Prima dell'invocazione di Ollama, il sistema tenta l'estrazione diretta:

| Formato | Libreria | Metadati Estratti |
|---|---|---|
| `.docx` | python-docx | author, last_modified_by, version, title, subject, keywords, created, modified, titoli (Heading1/2), sommario (TOC) |
| `.pdf` | PyPDF2 / pdfplumber | author, title, subject, creator, testo prime N pagine |
| `.xlsx` / `.xls` | openpyxl / xlrd | author, title, nomi dei fogli |
| `.doc` | antiword / conversione | Valutare conversione a docx o estrazione testo tramite tool esterni |

### 7.4 Gestione Errori e Fallback

| Situazione | Comportamento |
|---|---|
| Ollama non raggiungibile | Scanner continua con sola estrazione metadati diretta e auto-tagging da path. Analisi AI segnata come "pendente" per il prossimo ciclo |
| File troppo grande | Si inviano solo i primi N caratteri (configurabile, default: 100.000) |
| Risposta Ollama non parsabile | Si logga l'errore, si conservano solo i metadati diretti |
| `ollama.enabled = false` | Integrazione AI completamente disabilitata |

---

## 8. Gestione Revisioni

### 8.1 Pattern di Rilevamento

Il sistema riconosce più pattern per identificare revisioni e versioni superate di uno stesso documento.

#### Pattern 1: Revisione numerata standard `.R{NN}`

Formato: `{nome_base}.R{NN}.{estensione}`

Dove `{NN}` è un numero di revisione a due o più cifre (R00, R01, R02, ..., R10, R99).

**Regex:** `^(.+)\.R(\d{2,})\.(docx|doc|pdf|xlsx|xls|.+)$`

| File | nome_base | revisione |
|---|---|---|
| `GR_ELETTRONICA_TOBE_Modello_MES.R00.docx` | `GR_ELETTRONICA_TOBE_Modello_MES` | 00 |
| `GR_ELETTRONICA_TOBE_Modello_MES.R01.docx` | `GR_ELETTRONICA_TOBE_Modello_MES` | 01 |
| `Documento_Delivery_SI_Seitron_Integrazioni_R2.docx` | Pattern alternativo: `_R{N}` |

#### Pattern 2: Versione superata con `.old`

A volte le versioni superate vengono identificate inserendo **`.old`** nel nome del file, tipicamente prima dell'estensione o come estensione aggiuntiva.

Formato: `{nome_base}.old.{estensione}` oppure `{nome_base}.{estensione}.old`

**Regex:** `^(.+)\.old\.(docx|doc|pdf|xlsx|xls|.+)$` e `^(.+\.(docx|doc|pdf|xlsx|xls|.+))\.old$`

| File originale (principale) | File superato (.old) | Relazione |
|---|---|---|
| `Specifica_MES.docx` | `Specifica_MES.old.docx` | `.old` inserito prima dell'estensione |
| `Specifica_MES.docx` | `Specifica_MES.docx.old` | `.old` aggiunto dopo l'estensione |
| `Report_APS.R01.pdf` | `Report_APS.R01.old.pdf` | Combinazione revisione + old |

**Regole per il pattern `.old`:**
- Un file con `.old` nel nome è **sempre considerato una versione superata** (mai il documento principale)
- Il file corrispondente senza `.old` (se esiste) è il documento principale
- Se esistono sia `.old` che revisioni numerate (es. `file.R00.docx` + `file.old.docx`), la revisione numerata più alta senza `.old` è il principale
- Il suffisso `.old` può trovarsi in qualsiasi posizione nel nome, ma le varianti più comuni sono: `nome.old.ext` e `nome.ext.old`

#### Riepilogo Pattern Riconosciuti

| Pattern | Regex | Esempio | Tipo |
|---|---|---|---|
| `.R{NN}` | `\.R(\d{2,})\.` | `file.R01.docx` | Revisione numerata |
| `_R{N}` | `_R(\d+)\.` | `file_R2.docx` | Revisione numerata alternativa |
| `.old.{ext}` | `\.old\.` | `file.old.docx` | Versione superata |
| `.{ext}.old` | `\.\w+\.old$` | `file.docx.old` | Versione superata |

### 8.2 Logica di Raggruppamento

1. Per ogni file, verificare se il nome corrisponde a uno dei pattern di revisione o di versione superata (`.old`)
2. Estrarre il `nome_base` rimuovendo il suffisso di revisione/old
3. Raggruppare tutti i file con lo stesso `nome_base` nella stessa cartella cliente
4. Determinare il documento principale con questa priorità:
   - **Mai** un file con `.old` nel nome (è sempre una versione superata)
   - Tra i file senza `.old`: quello con il numero di revisione più alto
   - A parità di revisione: quello con la data di ultima modifica più recente
5. Tutte le altre versioni (revisioni precedenti + file `.old`) diventano **revisioni precedenti**
6. I file `.old` vengono ordinati per data decrescente dopo le revisioni numerate

### 8.3 Modello Dati

Nella tabella `documenti`, il campo `id_documento_principale`:

- **Documento principale**: `id_documento_principale = NULL` (è lui stesso il principale)
- **Revisioni precedenti**: `id_documento_principale = ID del documento principale`

```sql
-- Ottenere tutte le revisioni di un documento principale con id = X
SELECT * FROM documenti
WHERE id_documento_principale = X OR id_documento = X
ORDER BY documento_revisione DESC, documento_data_ultima_modifica DESC;
```

### 8.4 Aggiornamento su Nuova Revisione

Quando viene trovata una nuova revisione (es. R02 dove prima c'erano solo R00 e R01):

1. Il nuovo file (R02) diventa il documento principale
2. L'ex principale (R01) viene aggiornato con `id_documento_principale` → R02
3. Le classificazioni e i metadati manuali del vecchio principale vengono **propagati (copiati)** al nuovo principale, per non perdere il lavoro di classificazione già fatto

---

## 9. Sistema di Classificazione e Tag

### 9.1 Struttura Gerarchica

```
Area (livello 1)
  └── SottoArea (livello 2)
       └── SubArea (livello 3)
```

Ogni documento può avere **N combinazioni** di classificazione (relazione many-to-many via `documento_classificazione`).

**Esempio per un singolo documento:**

| Area | SottoArea | SubArea |
|---|---|---|
| MES | TRAC | ALL |
| MES | QUAL | PCNT |
| MES | QUAL | BMSC |
| MES | QUAL | DFDT |
| MES | PANA | ALL |

### 9.2 Auto-Classificazione da Percorso Cartella

Regole FIP basate sul nome della cartella (case-insensitive, wildcard):

| Pattern cartella | Tag FIP |
|---|---|
| `*PROJECT*MANAGEMENT*` | PRJM |
| `*ENGINEERING*` | ENGR |
| `*VISIONING*` | VISN |
| `*TRAINING*` | TRNG |
| `*PILOT*` | PILT |
| `*TEST*` | TEST |
| `*TUNING*` | TUNG |
| `*SUPPORT*` | SUPP |

**Esempi concreti dal filesystem:**
- `000 PROJECT MANAGEMENT` → FIP = PRJM
- `100 ENGINEERING` → FIP = ENGR
- `200 VISIONING` → FIP = VISN
- `500 TRAINING` → FIP = TRNG

### 9.3 Auto-Classificazione da Nome File

Keyword nel nome file per suggerire classificazioni Area:

| Keyword (case-insensitive) | Classificazione suggerita |
|---|---|
| `MES`, `MOM` | Area = MES |
| `APS`, `PLANNING`, `SCHEDULING` | Area = APS |
| `INTEGR`, `INTERFACE` | Area = INT |
| `INDUSTRY`, `4.0`, `5.0`, `IOT` | Area = IND |
| `KPI`, `REPORT`, `ANALISI` | Area = KPI |
| `TOBE`, `TO_BE`, `TO-BE` | Tipo Documento = TB |
| `QUALITY`, `QUALITA`, `QUALIT` | Area = MES, SottoArea = QUAL |
| `MANUTENZIONE` | Area = MES, SottoArea correlata |
| `ACQUIST`, `RICEVIMENT` | Area = OPM |

**Esempi dalla specifica originale:**

| Nome File | Classificazione |
|---|---|
| `FRIUL_FILIERE.Mes.Industry4.0.doc` | Area MES + Area IND |
| `Manuale ACQUISTI - RICEVIMENTI.docx` | Area OPM |
| `GR_ELETTRONICA_TOBE_Modello_MES.R00.docx` | Area MES + Tipo TB |
| `GRElettronicaTOBE_APS_V2.docx` | Area APS + Tipo TB |
| `Documento_Delivery_SI_Seitron_Integrazioni_R2.docx` | Area INT |
| `TRASV.Standard_Interface.20200622_NUOVO.docx` | Area INT |
| `Manutenzione in Promec.docx` | Area MES, SottoArea QUAL/Manutenzioni |
| `PMP-PROMEC_QUALITA.docx` | Area MES, SottoArea QUAL |

### 9.4 Workflow di Classificazione

```
                   Scanner inserisce
                   nuovo record
                         │
                         ▼
              ┌─────────────────────┐
              │ Non Classificato    │  ← Stato iniziale
              │ attivo = 0          │  ← Non attivo
              └─────────────────────┘
                         │
            Utente compila parzialmente
            (almeno un tag)
                         │
                         ▼
              ┌─────────────────────┐
              │ Parzialmente        │
              │ Classificato        │
              └─────────────────────┘
                         │
            Utente completa tutti i
            campi obbligatori e conferma
                         │
                         ▼
              ┌─────────────────────┐
              │ Classificato        │  ← Classificazione completa
              │ attivo = 1          │  ← Attivato
              └─────────────────────┘
```

**Campi obbligatori per "Classificato":** almeno una classificazione Area, almeno un tipo documento, settore assegnato.

### 9.5 Priorità Classificazione Manuale vs Automatica

- **Inserimento iniziale** (prima scansione): tutti i campi pre-compilati dall'auto-tagger e/o AI se possibile
- **Scansioni successive**: lo scanner aggiorna **SOLO** i campi ancora NULL/vuoti nel database
- I campi già compilati (manualmente o automaticamente) **NON vengono mai sovrascritti**
- **La classificazione manuale ha SEMPRE priorità su quella automatica**

---

## 10. Gestione Stati Documento

### 10.1 Diagramma di Transizione Stati

```
                    File trovato per la prima volta
                              │
                              ▼
                          ┌───────┐
                          │ NEW   │
                          └───────┘
                              │
              Scansione successiva, file ancora presente e non modificato
                              │
                              ▼
                          ┌───────┐
                          │ ESU   │  (Esistente Unico)
                          └───────┘
                           /    \
                          /      \
     File modificato     /        \    Trovato duplicato
     (hash diverso)     /          \   (stesso hash+nome in altro path)
                       ▼            ▼
                  ┌───────┐    ┌───────┐
                  │ MOD   │    │ EXD   │  (Esistente con Duplicati)
                  └───────┘    └───────┘
                                    │
                               Il duplicato:
                                    ▼
                               ┌───────┐
                               │ DUP   │  (record duplicato)
                               └───────┘

    File non trovato al percorso originale:

    ┌───────┐         Hash trovato in altro path?
    │ (any) │ ──────► Sì ────► ┌───────┐
    └───────┘                   │ SPO   │  (Spostato)
         │                      └───────┘
         │
         └──────────► No ────► ┌───────┐
                               │ CAN   │  (Cancellato)
                               └───────┘
```

### 10.2 Algoritmo di Determinazione Stato

**Per record esistenti nel DB durante una scansione:**

```python
def determina_stato(record_db, file_trovato, hash_attuale, tutti_i_file):
    if not file_trovato:
        # Il file al percorso_relativo non esiste più
        if hash_attuale in [f.hash for f in tutti_i_file if f.percorso != record_db.percorso]:
            return 'SPO'  # Spostato
        else:
            return 'CAN'  # Cancellato
    else:
        # Il file esiste ancora
        if hash_attuale != record_db.documento_hash:
            return 'MOD'  # Modificato
        else:
            # Hash uguale, non modificato → controlliamo duplicati
            stessi = [f for f in tutti_i_file
                     if f.hash == hash_attuale and f.nome == record_db.documento_nome_file]
            if len(stessi) > 1:
                return 'EXD'  # Esistente con Duplicati
            else:
                return 'ESU'  # Esistente Unico
```

**Per nuovi file (non presenti nel DB):**

```python
def stato_nuovo_file(hash_file, nome_file, tutti_i_record_db):
    esistenti = [r for r in tutti_i_record_db
                if r.documento_hash == hash_file and r.documento_nome_file == nome_file]
    if esistenti:
        return 'DUP'  # Duplicato di un file già censito
    else:
        return 'NEW'  # Completamente nuovo
```

### 10.3 Dettaglio Significato Stati

| Codice | Nome | Condizione | Azione Scanner |
|---|---|---|---|
| NEW | Nuovo | File non in DB, hash unico | INSERT |
| ESU | Esistente Unico | File presente, hash invariato, nessun duplicato | UPDATE timestamp |
| MOD | Modificato | File presente, hash diverso | UPDATE hash + timestamp |
| CAN | Cancellato | Percorso non esiste, hash non trovato altrove | UPDATE stato |
| SPO | Spostato | Percorso non esiste, hash trovato altrove | UPDATE stato + percorso |
| DUP | Duplicato | Stesso hash+nome in percorso diverso (record secondario) | INSERT con stato DUP |
| EXD | Esistente con Duplicati | File originale + almeno un duplicato altrove | UPDATE stato |

---

## 11. Requisiti Non Funzionali

### 11.1 Performance

| Metrica | Target |
|---|---|
| Scansione completa senza AI | < 1 ora per ~216.000 file |
| Scansione completa con AI | < 8 ore per ~216.000 file |
| Scansione incrementale (solo nuovi/modificati) | Riduzione drastica rispetto a scansione completa |
| Risposta ricerche web | < 2 secondi per dataset fino a 250.000 record |
| Indicizzazione DB | Indici su tutte le colonne usate nei filtri |

### 11.2 Affidabilità

- **Crash recovery**: transazioni SQLite (`BEGIN`/`COMMIT`/`ROLLBACK`) per ogni batch
- **File lock**: gestione corretta di file aperti da altri utenti (skip con logging, retry al ciclo successivo)
- **Timeout Ollama**: timeout configurabile con fallback a classificazione senza AI
- **Logging**: log dettagliato per ogni esecuzione (file processati, errori, warning, statistiche)

### 11.3 Sicurezza

- Applicazione web ad **uso interno aziendale** (non esposta a Internet)
- Accesso **in sola lettura** al filesystem di rete (lo scanner non modifica mai i file)
- Database SQLite posizionato su percorso con **backup automatico**
- Autenticazione: semplice (username/password) o integrazione AD (fase successiva)

### 11.4 Manutenibilità

- Codice Python con **type hints** e docstring
- Struttura **modulare** (singola responsabilità per modulo)
- File di configurazione **esternalizzati** (nessun valore hardcoded)
- Logging strutturato con livelli configurabili
- Modalità **"dry-run"** per simulazione senza scrittura su DB

### 11.5 Scalabilità

- Design DB modulare: nuovi tag, aree, settori aggiungibili senza modifiche schema
- Nuovi percorsi base aggiungibili alla configurazione
- Passaggio futuro a PostgreSQL con modifiche minime (astrazione layer DB)
- Possibile futura integrazione con Elasticsearch per full-text search avanzato

### 11.6 Compatibilità

| Componente | Supporto |
|---|---|
| **Formati fase 1** | .docx, .doc, .pdf, .xlsx, .xls |
| **Formati fase 2** | .pptx, .txt, .csv, .odt, .ods |
| **Sistemi operativi** | Windows (primario, percorsi UNC), Linux (secondario) |
| **Browser web** | Chrome, Edge (ultimi 2 major release) |
| **Python** | 3.10+ |

---

## 12. Piano di Verifica e Test

### 12.1 Test Unitari

| Modulo | Test | Descrizione |
|---|---|---|
| `directory_walker` | `test_filter_by_extension` | Solo i formati configurati vengono inclusi |
| `directory_walker` | `test_filter_by_date` | Filtro data (giorni indietro e range) |
| `directory_walker` | `test_include_exclude_dirs` | Logica include/exclude directory |
| `directory_walker` | `test_missing_censimento_filtro` | Skip se manca il file di filtro |
| `file_hasher` | `test_hash_consistency` | Stesso file → stesso hash |
| `file_hasher` | `test_hash_different_content` | File diversi → hash diversi |
| `revision_detector` | `test_detect_revision_pattern` | Riconosce .R00, .R01, .R02 |
| `revision_detector` | `test_group_revisions` | Raggruppa revisioni correttamente |
| `revision_detector` | `test_identify_latest` | Identifica revisione più recente come principale |
| `revision_detector` | `test_alternative_patterns` | Gestisce `_R2`, `_Rev01` e pattern alternativi |
| `revision_detector` | `test_old_suffix_before_ext` | Riconosce `file.old.docx` come versione superata |
| `revision_detector` | `test_old_suffix_after_ext` | Riconosce `file.docx.old` come versione superata |
| `revision_detector` | `test_old_never_principal` | File `.old` non diventa mai documento principale |
| `revision_detector` | `test_old_combined_with_revision` | Gestisce `file.R01.old.docx` (revisione superata) |
| `revision_detector` | `test_old_grouping_with_original` | `file.old.docx` + `file.docx` → `file.docx` è il principale |
| `status_tracker` | `test_new_file` | File nuovo → stato NEW |
| `status_tracker` | `test_unchanged_file` | File non modificato → stato ESU |
| `status_tracker` | `test_modified_file` | Hash diverso → stato MOD |
| `status_tracker` | `test_deleted_file` | File non trovato, hash assente altrove → CAN |
| `status_tracker` | `test_moved_file` | File non trovato, hash presente altrove → SPO |
| `status_tracker` | `test_duplicated_file` | Stesso hash e nome in altro percorso → DUP/EXD |
| `metadata_extractor` | `test_extract_docx_metadata` | Estrae autore, titolo, versione da docx |
| `metadata_extractor` | `test_extract_pdf_metadata` | Estrae metadati da PDF |
| `metadata_extractor` | `test_extract_xlsx_metadata` | Estrae metadati da Excel |
| `auto_tagger` | `test_fip_from_folder_name` | "200 VISIONING" → FIP=VISN |
| `auto_tagger` | `test_area_from_filename` | "..._MES_..." → Area=MES |
| `auto_tagger` | `test_manual_priority` | Classificazione manuale non sovrascritta |
| `ai_classifier` | `test_ollama_response_parsing` | Parsing corretto risposta JSON da Ollama |
| `ai_classifier` | `test_ollama_timeout` | Fallback se Ollama non risponde |
| `database/repository` | `test_insert_document` | INSERT corretto in tabella documenti |
| `database/repository` | `test_update_document` | UPDATE con preservazione campi manuali |
| `database/repository` | `test_classification_crud` | CRUD su documento_classificazione |

### 12.2 Test di Integrazione

| Test | Descrizione |
|---|---|
| `test_full_scan_new_directory` | Scansione directory di test con file nuovi → INSERT e stati NEW |
| `test_full_scan_modified_files` | Seconda scansione dopo modifica file → stati MOD |
| `test_full_scan_deleted_files` | Seconda scansione dopo rimozione file → stato CAN |
| `test_full_scan_moved_files` | Seconda scansione dopo spostamento file → stato SPO |
| `test_full_scan_duplicated_files` | Scansione con duplicati → stati DUP/EXD |
| `test_revision_chain` | Scansione con file R00, R01, R02 → catena revisioni |
| `test_new_revision_added` | Aggiunta R03 a catena esistente → cambio principale |
| `test_old_suffix_revision` | Scansione con `file.docx` + `file.old.docx` → file.docx è principale, file.old.docx è precedente |
| `test_mixed_old_and_numbered` | Scansione con `file.R00.docx` + `file.R01.docx` + `file.old.docx` → R01 è principale, R00 e .old sono precedenti |
| `test_ollama_integration` | Invio documento reale a Ollama e parsing risposta |
| `test_web_search` | Ricerca dalla UI con filtri multipli → risultati corretti |
| `test_web_edit_classification` | Modifica classificazione da UI → persistenza in DB |
| `test_config_override` | Filtro locale sovrascrive filtro globale |

### 12.3 Test di Accettazione (UAT)

| Scenario | Procedura | Risultato Atteso |
|---|---|---|
| Censimento iniziale | Posizionare censimento_filtro.json, avviare scanner | Tutti i file configurati censiti con stato NEW |
| Classificazione manuale | Aprire un documento, assegnare Area+SottoArea+SubArea | Record aggiornato, classificazione = "Parzialmente Classificato" |
| Ricerca per keyword | Cercare "tracciabilità" nella barra di ricerca | Documenti con parola chiave corrispondente restituiti |
| Filtro per directory | Deselezionare cartella nel tree view | Documenti di quella cartella non mostrati |
| Apertura file | Cliccare "Apri File" su un documento | File aperto con applicazione predefinita |
| Rilevamento revisione numerata | File R00 e R01 nella stessa cartella | R01 è principale, R00 è revisione precedente |
| Rilevamento versione .old | `Specifica.docx` + `Specifica.old.docx` nella stessa cartella | `Specifica.docx` è principale, `.old` è precedente |
| Riscansione con modifiche | Modificare un file, rieseguire scanner | File con stato MOD, hash aggiornato |
| Non sovrascrittura manuale | Classificare manualmente, rieseguire scanner | Classificazione manuale preservata |

### 12.4 Test di Performance

| Test | Metrica | Target |
|---|---|---|
| Scansione 10.000 file (senza AI) | Tempo totale | < 10 minuti |
| Scansione 10.000 file (con AI) | Tempo totale | < 4 ore |
| Scansione incrementale (100 modificati su 10.000) | Tempo totale | < 5 minuti |
| Ricerca web su 100.000 record | Tempo risposta | < 2 secondi |
| Filtro multi-criterio su 100.000 record | Tempo risposta | < 3 secondi |

---

## 13. Appendici

### 13.1 Dipendenze Python Previste

| Libreria | Scopo |
|---|---|
| `python-docx` | Lettura metadati e contenuto .docx |
| `PyPDF2` (o `pdfplumber`) | Lettura metadati e contenuto .pdf |
| `openpyxl` | Lettura metadati .xlsx |
| `xlrd` | Lettura metadati .xls |
| `flask` | Web framework |
| `requests` | Chiamate HTTP a Ollama |
| `apscheduler` | Scheduling scansione periodica |
| `hashlib` | (stdlib) Calcolo hash SHA-256 |
| `pathlib` | (stdlib) Gestione percorsi |
| `sqlite3` | (stdlib) Accesso database |
| `logging` | (stdlib) Logging |
| `json` | (stdlib) Parsing configurazione |

### 13.2 Decisioni Prese

Le seguenti questioni sono state risolte con il committente:

| # | Questione | Decisione |
|---|---|---|
| 1 | **Codice tipo documento per Avanzamento/Appunti** | **"AV"** = Avanzamento Progetto, **"AP"** = Appunti |
| 2 | **Pattern revisione** | Utilizzare i pattern definiti: `.R{NN}`, `_R{N}`, `.old.{ext}`, `.{ext}.old`. Eventuali pattern aggiuntivi saranno valutati in corso d'opera |
| 3 | **Settore** | Il settore è una proprietà del **cliente** (tabella `cliente`), non del singolo documento |
| 4 | **Autenticazione web UI** | Fase 1: accesso libero (rete interna) |
| 5 | **Formati `.doc` e `.xls` legacy** | Utilizzare le librerie Python disponibili (python-docx, xlrd). Nessuna conversione via LibreOffice per ora |
| 6 | **Dimensione massima per analisi AI** | **100.000 caratteri** (configurabile) |
| 7 | **Backup database** | Copia automatica del file SQLite **prima di ogni scansione** |
| 8 | **Campi obbligatori per "Classificato"** | Almeno una classificazione Area, almeno un tipo documento, settore assegnato al cliente |

---

***** FINE DOCUMENTO *****
