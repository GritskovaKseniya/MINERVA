# Minerva Web - Istruzioni d'uso

## Panoramica

Minerva Web (`run_web.py`) e' l'interfaccia web per la consultazione, ricerca e classificazione manuale dei documenti censiti dallo Scanner. Offre:

- Elenco documenti con filtri avanzati (cliente, stato, area, settore, classificazione, directory)
- Ricerca full-text nel contenuto dei documenti
- Pagina dettaglio per visualizzare metadati, revisioni e classificazioni
- Modifica manuale della classificazione (area, tipo documento, FIP, stato)
- Apertura/download del file originale
- Gestione clienti e assegnazione settore

## Prerequisiti

- Python 3.10+
- Dipendenze installate: `pip install -r requirements.txt`
- File di configurazione `minerva_config.json`
- Database SQLite popolato dallo Scanner (almeno una scansione eseguita)

## Avvio

```bash
python run_web.py [opzioni]
```

| Opzione | Descrizione |
|---|---|
| `-c`, `--config PERCORSO` | Percorso del file di configurazione (default: `minerva_config.json`) |
| `--debug` | Attiva la modalita' debug di Flask (reload automatico, messaggi dettagliati) |

### Esempi

```bash
# Avvio standard
python run_web.py

# Avvio in modalita' debug (per sviluppo)
python run_web.py --debug

# Con configurazione personalizzata
python run_web.py -c /percorso/altro_config.json
```

Una volta avviato, l'interfaccia e' raggiungibile all'indirizzo:

```
http://localhost:5000
```

Host e porta sono configurabili nel file `minerva_config.json` (sezione `web`).

## Configurazione Web

Nel file `minerva_config.json`:

```json
{
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false,
        "results_per_page": 50
    }
}
```

| Campo | Descrizione | Default |
|---|---|---|
| `host` | Indirizzo di ascolto (`0.0.0.0` = tutte le interfacce) | `0.0.0.0` |
| `port` | Porta TCP | `5000` |
| `debug` | Modalita' debug Flask | `false` |
| `results_per_page` | Risultati per pagina nelle tabelle | `50` |

## Pagine dell'interfaccia

### 1. Elenco Documenti (`/documents`)

Pagina principale. Mostra una tabella con tutti i documenti censiti dallo Scanner.

#### Filtri disponibili

| Filtro | Descrizione |
|---|---|
| **Cliente** | Filtra per cartella cliente |
| **Testo** | Cerca nel nome file e nel percorso |
| **Stato** | Filtra per stato documento (NEW, ESU, MOD, CAN, SPO, DUP, EXD) |
| **Classificazione** | Non Classificato / Parzialmente Classificato / Classificato |
| **Attivo** | Filtra per flag attivo/non attivo |
| **Area** | Filtra per area tematica (MES, APS, OPM, INT, IND, KPI) |
| **Settore** | Filtra per settore produttivo del cliente |
| **Directory** | Filtra per sotto-directory (disponibile dopo aver selezionato un cliente) |

I filtri sono combinabili tra loro. La selezione di un cliente abilita il filtro per directory con un albero di navigazione.

#### Colorazione delle righe

| Colore | Significato |
|---|---|
| Verde | Classificato e attivo |
| Verde chiaro | Classificato e non attivo |
| Giallo | Parzialmente classificato e attivo |
| Giallo chiaro | Parzialmente classificato e non attivo |
| Grigio | Non classificato e attivo |
| Grigio chiaro | Non classificato e non attivo |
| Rosso | Documento cancellato (stato CAN) |

#### Revisioni

Nella tabella, accanto al nome del file viene indicato il numero di revisioni correlate. Cliccando si espande il dettaglio delle revisioni (nome file, data, stato).

#### Paginazione

I risultati sono paginati. I controlli di navigazione si trovano in fondo alla tabella.

### 2. Ricerca Full-Text (`/search`)

Pagina per la ricerca nel contenuto dei documenti tramite l'indice FTS5.

#### Come cercare

- Digitare una o piu' parole nel campo di ricerca
- Opzionalmente selezionare un cliente per restringere i risultati
- Premere Invio o il pulsante di ricerca

#### Sintassi di ricerca

| Esempio | Significato |
|---|---|
| `manuale utente` | Cerca documenti che contengono "manuale" E "utente" |
| `"manuale utente"` | Cerca la frase esatta "manuale utente" |
| `manuale OR utente` | Cerca documenti che contengono "manuale" OPPURE "utente" |
| `manuale NOT installazione` | Cerca "manuale" escludendo documenti con "installazione" |
| `manu*` | Cerca parole che iniziano con "manu" (manuale, manutenzione...) |

#### Risultati

Ogni risultato mostra:
- Nome del file (cliccabile per aprire il dettaglio)
- Cliente e percorso
- Frammento di testo con i termini cercati **evidenziati**
- Stato e classificazione del documento

I risultati sono ordinati per rilevanza (algoritmo BM25).

### 3. Dettaglio Documento (`/documents/<id>`)

Pagina di dettaglio per un singolo documento. Si accede cliccando su un documento nella lista o nei risultati di ricerca.

#### Sezioni

**Informazioni file**: Nome, percorso, dimensione, date di creazione e ultima modifica, hash, stato.

**Metadati estratti**: Autore, titolo, parole chiave, versione interna, sommario - estratti automaticamente dal contenuto del file.

**Classificazione**: Form per la modifica manuale di:
- Stato classificazione (Non Classificato / Parzialmente / Classificato)
- Flag attivo
- Descrizione e progetto
- Titolo e parole chiave
- Aree tematiche (selezione multipla con gerarchia Area > SottoArea > SubArea)
- Tipi documento (selezione multipla)
- FIP (selezione multipla)

**Revisioni**: Se il documento ha revisioni correlate, vengono elencate con nome, data e stato. Il documento principale (versione attuale) e' evidenziato.

#### Modifica classificazione

1. Compilare i campi desiderati nella sezione Classificazione
2. Per aggiungere un'area: selezionare Area, opzionalmente SottoArea e SubArea
3. Per aggiungere un tipo documento o FIP: selezionare dalla lista
4. Cliccare **Salva** per confermare le modifiche

**Regola di priorita'**: Le classificazioni manuali inserite dall'interfaccia web non vengono mai sovrascritte dallo Scanner nelle scansioni successive. Lo Scanner aggiorna solo i campi non ancora compilati manualmente.

#### Apertura file

Il pulsante **Apri file** permette di scaricare/aprire il file originale direttamente dal browser. Il file viene servito dal percorso originale nel filesystem.

### 4. Clienti (`/clienti`)

Pagina con l'elenco dei clienti rilevati durante le scansioni.

Per ogni cliente viene mostrato:
- Nome della cartella cliente
- Percorso base
- Numero di documenti censiti
- Settore produttivo assegnato

#### Assegnazione settore

Per assegnare un settore ad un cliente:
1. Selezionare il settore dal menu a tendina nella riga del cliente
2. Confermare la selezione

I settori disponibili sono predefiniti nel database (24+ settori produttivi).

## API JSON

L'interfaccia espone alcune API per il caricamento dinamico dei dati:

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/api/sotto_aree/<id_area>` | GET | Restituisce le sotto-aree di un'area |
| `/api/sub_aree/<id_sotto_area>` | GET | Restituisce le sub-aree di una sotto-area |
| `/api/directories/<cliente>` | GET | Restituisce l'albero directory di un cliente |

Queste API sono utilizzate internamente dall'interfaccia per il caricamento a cascata dei filtri di classificazione.

## Risoluzione problemi

| Problema | Soluzione |
|---|---|
| Pagina vuota, nessun documento | Eseguire prima lo Scanner: `python run_scanner.py` |
| Ricerca full-text senza risultati | Verificare che lo Scanner sia stato eseguito con l'indice FTS attivo. Se necessario, rigenerare: `python run_scanner.py --regenerate` |
| "Apri file" restituisce 404 | Il file originale e' stato spostato o cancellato dal filesystem. Rieseguire lo Scanner per aggiornare lo stato |
| Filtro directory non appare | Selezionare prima un cliente dal filtro apposito |
| Classificazione non salvata | Verificare di aver cliccato il pulsante Salva dopo le modifiche |
| Errore di connessione al DB | Verificare che il percorso `database.path` in `minerva_config.json` sia corretto e che il file `.db` esista |
