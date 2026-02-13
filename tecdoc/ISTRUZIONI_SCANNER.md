# Minerva Scanner - Istruzioni d'uso

## Panoramica

Lo Scanner Minerva (`run_scanner.py`) è il componente batch che censisce e analizza automaticamente i documenti presenti nelle directory configurate. Ad ogni esecuzione:

1. Scansiona le cartelle clienti alla ricerca di file nei formati configurati
2. Calcola l'hash SHA-256 di ogni file per rilevare modifiche, duplicati e spostamenti
3. Estrae metadati dal filesystem e dal contenuto dei file (autore, titolo, parole chiave, testo)
4. Classifica automaticamente i documenti tramite AI locale (Ollama) se disponibile
5. Rileva revisioni di documenti (pattern `.R00/.R01`, `_R1`, `.old`, `new`, cartelle `old`)
6. Aggiorna il database SQLite con lo stato di ogni documento (NEW, ESU, MOD, CAN, SPO, DUP)
7. Indicizza il contenuto per la ricerca full-text (FTS5)

## Prerequisiti

### Requisiti base

- Python 3.10+
- Dipendenze installate: `pip install -r requirements.txt`
- File di configurazione `minerva_config.json` presente nella directory di lavoro

### Ollama (opzionale, per classificazione AI)

La classificazione automatica tramite AI richiede Ollama in esecuzione localmente.

**Installazione Ollama:**

1. Scarica Ollama da [https://ollama.com/download](https://ollama.com/download)
2. Installa l'applicazione per Windows
3. Verifica che Ollama sia in esecuzione:
   ```bash
   curl http://localhost:11434/api/tags
   ```

**Installazione modello llama3.2:**

```bash
ollama pull llama3.2:latest
```

**Verifica modelli installati:**

```bash
ollama list
```

**Configurazione:**

Nel file `minerva_config.json`, assicurati che Ollama sia abilitato:

```json
"ollama": {
    "base_url": "http://localhost:11434",
    "model": "llama3.2:latest",
    "enabled": true
}
```

Per disabilitare la classificazione AI, imposta `"enabled": false`.

## Avvio

```bash
python run_scanner.py [opzioni]
```

## Opzioni da linea di comando

| Opzione | Descrizione |
|---|---|
| `-c`, `--config PERCORSO` | Percorso del file di configurazione (default: `minerva_config.json`) |
| `--dry-run` | Esegue la scansione senza modificare il database (solo log) |
| `--regenerate` | Cancella tutti i documenti dal database e riscansiona da zero |
| `--path PERCORSO` | Scansiona solo un file o sottocartella specifica |

### Esempi

```bash
# Scansione completa standard
python run_scanner.py

# Scansione di prova (senza modificare il DB)
python run_scanner.py --dry-run

# Rigenerazione completa del database
python run_scanner.py --regenerate

# Scansiona solo un cliente specifico
python run_scanner.py --path "ClienteX"

# Scansiona solo una sottocartella
python run_scanner.py --path "ClienteX/progetto/documentazione"

# Scansiona un singolo file
python run_scanner.py --path "ClienteX/progetto/doc.docx"

# Usa un file di configurazione alternativo
python run_scanner.py -c /percorso/altro_config.json
```

## Configurazione

### File globale: `minerva_config.json`

```json
{
    "database": {
        "path": "./data/minerva.db",
        "backup_enabled": true,
        "backup_path": "./data/backups/"
    },
    "percorsi_base": [
        {
            "nome": "NomePercorso",
            "percorso": "C:\\Percorso\\Ai\\Documenti",
            "tipo": "clienti"
        }
    ],
    "scanner": {
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
        "model": "llama3.2:latest",
        "timeout_seconds": 120,
        "max_retries": 3,
        "max_text_chars": 100000,
        "enabled": true
    },
    "logging": {
        "level": "INFO",
        "file": "./logs/minerva.log",
        "max_size_mb": 50,
        "backup_count": 5
    }
}
```

#### Sezioni di configurazione

**database**: Percorso del database SQLite e impostazioni backup.

**percorsi_base**: Lista dei percorsi radice da scansionare. Ogni percorso contiene sotto-directory che rappresentano clienti. Il campo `tipo` indica la modalita' di organizzazione (`clienti`).

**scanner.filtro_globale_default**: Filtri applicati globalmente a tutte le scansioni:
- `formati_da_leggere`: Formati file da includere (glob pattern, es. `*.docx`)
- `filtro_data`: Filtro temporale opzionale (per data di ultima modifica)
  - `usa_giorni_all_indietro`: Se `true`, filtra per N giorni nel passato
  - `giorni_all_indietro`: Numero di giorni (usato se `usa_giorni_all_indietro` e' `true`)
  - `data_inizio` / `data_fine`: Intervallo date esplicito (formato ISO, es. `2024-01-01`)

**scanner.hash_algorithm**: Algoritmo di hashing (`sha256`).

**scanner.max_file_size_mb**: Dimensione massima dei file da processare (in MB).

**ollama**: Configurazione del servizio AI locale:
- `enabled`: Attiva/disattiva la classificazione AI
- `base_url`: URL del server Ollama
- `model`: Modello da utilizzare (es. `llama3.2:latest`)
- `timeout_seconds`: Timeout per ogni richiesta
- `max_text_chars`: Massimo numero di caratteri inviati al modello

**logging**: Configurazione del logging (livello, file, rotazione).

### File locale per cliente: `censimento_filtro.json`

Ogni cartella cliente puo' contenere un file `censimento_filtro.json` per personalizzare i filtri. I campi presenti sovrascrivono i default globali, quelli assenti vengono ereditati.

**Importante**: Se il file `censimento_filtro.json` non esiste nella cartella di un cliente, quel cliente viene saltato dalla scansione.

```json
{
    "censimento_filtro": {
        "directory_da_leggere": ["/*"],
        "directory_da_evitare": ["archivio_vecchio", "temp"],
        "formati_da_leggere": ["*.docx", "*.pdf"],
        "filtro_data": {
            "usa_giorni_all_indietro": true,
            "giorni_all_indietro": 365
        }
    }
}
```

| Campo | Descrizione | Default |
|---|---|---|
| `directory_da_leggere` | Sotto-directory da includere (`/*` = tutte) | `["/*"]` |
| `directory_da_evitare` | Sotto-directory da escludere | `[]` |
| `formati_da_leggere` | Formati file (override del globale) | da config globale |
| `filtro_data` | Filtro date (override del globale) | da config globale |

## Formati file supportati

Lo scanner estrae metadati e testo dai seguenti formati:

| Formato | Estensione | Metadati estratti |
|---|---|---|
| Microsoft Word | `.docx` | Autore, titolo, parole chiave, titoli (heading), testo completo |
| Microsoft Word legacy | `.doc` | Solo metadati filesystem |
| PDF | `.pdf` | Autore, titolo, parole chiave, testo completo |
| Microsoft Excel | `.xlsx` | Autore, titolo, nomi fogli |
| Microsoft Excel legacy | `.xls` | Autore, nomi fogli |

## Rilevamento revisioni

Lo scanner riconosce automaticamente le revisioni di un documento tramite diversi pattern:

| Pattern | Esempio | Comportamento |
|---|---|---|
| `.R{NN}` | `doc.R00.docx`, `doc.R01.pdf` | Revisione numerata; numero piu' alto = piu' recente |
| `_R{N}` | `doc_R2.docx` | Revisione numerata alternativa |
| `.old` nel nome | `doc.old.docx`, `doc.docx.old` | Marcato come versione precedente |
| `new` nel nome | `doc_new.docx`, `doc new.pdf` | Raggruppato con la versione senza "new" |
| Cartella `old` | `cliente/old/doc.docx` | Tutti i file nella cartella sono versioni precedenti |

Le revisioni vengono raggruppate per nome base e directory. Il documento principale (versione attuale) viene determinato in base a:
1. Non si trova in una cartella `old` e non ha `.old` nel nome
2. Ha il numero di revisione piu' alto
3. A parita', ha la data di creazione piu' recente

## Stati dei documenti

| Stato | Codice | Significato |
|---|---|---|
| Nuovo | `NEW` | File appena trovato, prima scansione |
| Esistente | `ESU` | File gia' presente, nessuna modifica |
| Modificato | `MOD` | Il contenuto del file e' cambiato (hash diverso) |
| Cancellato | `CAN` | Il file non e' piu' presente nel filesystem |
| Spostato | `SPO` | Il file e' stato spostato (hash uguale, percorso diverso) |
| Duplicato | `DUP` | Esiste un altro file con lo stesso hash |
| Escluso da data | `EXD` | Il file e' fuori dal range di date configurato |

**Nota**: Lo scanner non cancella mai record dal database. I file non piu' presenti vengono marcati come `CAN` ma restano nel DB.

## Classificazione AI (Ollama)

Se Ollama e' attivo e raggiungibile, lo scanner invia il testo estratto al modello AI per ottenere:
- **Parole chiave** (max 20)
- **Riassunto** del contenuto (max 200 parole)
- **Aree tematiche suggerite** (OPM, MES, APS, INT, IND, KPI)
- **Tipo documento suggerito** (SC, SS, TS, MU, CU, NU, GA, AV, SV, TB, CR, AP, MN)

Se Ollama non e' disponibile, la scansione prosegue senza classificazione AI (i campi restano vuoti).

## Auto-tagging

Indipendentemente dalla AI, lo scanner assegna automaticamente tag basandosi su:
- **Percorso cartella**: es. una cartella "200 VISIONING" suggerisce FIP=VISN
- **Nome file**: es. un file contenente "_MES_" suggerisce Area=MES

## Indicizzazione Full-Text (FTS5)

Ogni documento scansionato viene indicizzato per la ricerca full-text. I campi indicizzati sono:
- Nome file
- Titolo del documento
- Testo contenuto
- Parole chiave
- Titoli estratti (heading)
- Sommario

L'indice FTS5 viene aggiornato automaticamente ad ogni scansione (per file nuovi e modificati).

## Log

I log vengono scritti su file (configurabile in `minerva_config.json`) e su console. Il livello di log predefinito e' `INFO`.

Percorso log predefinito: `./logs/minerva.log`

Al termine di ogni scansione viene stampato un riepilogo con le statistiche:
- Clienti processati
- File trovati, nuovi, modificati, cancellati, spostati, duplicati
- Revisioni rilevate
- Classificazioni AI effettuate
- Errori riscontrati
- Tempo totale

## Uso con `--path` (scansione selettiva)

L'opzione `--path` consente di limitare la scansione a un sotto-insieme dei file. Utile per:
- Riscansionare un singolo documento dopo una correzione
- Aggiornare solo i file di un cliente specifico
- Testare la scansione su una sottocartella

**Nota**: Quando si usa `--path`, il rilevamento di file cancellati (`CAN`) e spostati (`SPO`) viene disattivato per evitare falsi positivi.

## Uso con `--regenerate`

L'opzione `--regenerate` cancella tutti i documenti dal database prima di avviare la scansione. Utile quando:
- Lo schema del database e' cambiato
- Si vogliono ricaricare tutti i dati da zero
- L'indice FTS necessita di una ricostruzione completa

**Attenzione**: Le classificazioni manuali effettuate dall'interfaccia web verranno perse.
