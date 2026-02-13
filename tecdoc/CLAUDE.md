# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Minerva** is a document classification and census system for technical documentation. It consists of two main components that share a single SQLite database:

1. **Scanner** (`run_scanner.py`) - Batch component that discovers, analyzes, and classifies documents
2. **Web UI** (`run_web.py`) - Flask web interface for searching and manually classifying documents

The system is designed to scan client directories, extract metadata, compute content hashes for change detection, and optionally classify documents using local AI (Ollama).

## Common Commands

### Scanner (Batch Processing)

```bash
# Install dependencies
pip install -r requirements.txt

# Standard full scan
python run_scanner.py

# Dry-run (no DB changes)
python run_scanner.py --dry-run

# Regenerate database from scratch
python run_scanner.py --regenerate

# Scan specific client or file
python run_scanner.py --path "ClientName"
python run_scanner.py --path "ClientName/project/doc.docx"

# Use alternate config
python run_scanner.py -c /path/to/config.json
```

### Web Interface

```bash
# Start web server
python run_web.py

# Start in debug mode
python run_web.py --debug

# Access UI
# http://localhost:5000
```

## Architecture & Key Concepts

### Core Data Model

The canonical unique key for documents is **`percorso_relativo`** (relative path). Never rely on absolute network paths.

- **`percorso_base`** - Root path from configuration
- **`percorso_relativo`** - Relative path from client root (unique identifier)
- **`documento_hash`** - SHA-256 content hash for change detection

### Client Opt-In Mechanism

A client directory is only scanned if it contains a `censimento_filtro.json` file. Missing file = client skipped.

The `censimento_filtro.json` can override global filters:
- `directory_da_leggere` - Subdirectories to include
- `directory_da_evitare` - Subdirectories to exclude
- `formati_da_leggere` - File formats (glob patterns)
- `filtro_data` - Date filters

### Document States

Documents track their lifecycle through status codes:
- `NEW` - Newly discovered file
- `ESU` - Existing file, unchanged
- `MOD` - Modified (hash changed)
- `CAN` - Deleted from filesystem (soft delete, remains in DB)
- `SPO` - Moved (same hash, different path)
- `DUP` - Duplicate (another file with same hash exists)
- `EXD` - Excluded by date filter

### Revision Detection

The scanner automatically groups document revisions using patterns:
- `.R{NN}` suffix (e.g., `doc.R00.docx`, `doc.R01.pdf`)
- `_R{N}` suffix (e.g., `doc_R2.docx`)
- `.old` in filename
- `new` in filename
- Files in `old/` directories

The most recent revision is determined by: highest revision number > newest creation date.

### Manual vs. Automatic Classification

**Critical Rule**: Manual classifications from the Web UI are never overwritten by subsequent scans. The Scanner only updates fields that are NULL/empty.

### Configuration

Main config file: `minerva_config.json`
- Database path and backup settings
- Scanner paths (`percorsi_base`) and filters
- Ollama AI configuration
- Web server settings
- Logging configuration

## Module Structure

```
minerva/
├── config/
│   └── settings.py              # Configuration loading
├── database/
│   ├── models.py                # SQLite schema definitions
│   ├── repository.py            # DB access layer (CRUD)
│   └── migrations.py            # Schema migrations and backups
├── scanner/
│   ├── orchestrator.py          # Main scan orchestration
│   ├── directory_walker.py      # Filesystem enumeration
│   ├── file_hasher.py           # SHA-256 hashing
│   ├── metadata_extractor.py    # Extract from .docx, .pdf, .xlsx, etc.
│   ├── ai_classifier.py         # Ollama integration
│   ├── auto_tagger.py           # Rule-based classification
│   ├── revision_detector.py     # Revision grouping logic
│   └── status_tracker.py        # Document state determination
├── web/
│   ├── app.py                   # Flask application factory
│   ├── templates/               # Jinja2 templates
│   └── static/                  # CSS, JS
└── utils/
    └── logging_config.py        # Logging setup
```

## Database Schema Highlights

Key tables:
- `documenti` - Main document table (file metadata, hash, paths, classification)
- `cliente` - Client information and assigned sector
- `area` / `sotto_area` / `sub_area` - Hierarchical classification taxonomy
- `tipo_documento` - Document types (SC, SS, TS, MU, etc.)
- `fip` - FIP codes (project phases)
- `documenti_fts` - FTS5 full-text search index

## Supported File Formats

Scanner extracts metadata and text from:
- **Microsoft Word**: `.docx` (full metadata + text), `.doc` (filesystem only)
- **PDF**: `.pdf` (metadata + text)
- **Excel**: `.xlsx` (metadata + sheet names), `.xls` (limited)
- **Others**: `.txt`, `.xml`, `.sql`, `.cmd`, `.ksh`, `.eml`, `.ppt`, `.pptx`, `.mpp`

## Important Conventions

### Italian Domain Vocabulary

Preserve Italian terminology from the PRD and codebase:
- `percorso_relativo`, `percorso_base`
- `censimento_filtro.json`
- `documento_hash`
- `cliente_cartella`
- State codes: `ESU`, `MOD`, `CAN`, `SPO`, `DUP`

### Code Comments and Messages

Default to Italian for inline comments and commit messages, consistent with existing codebase and PRD documentation.

### Commit Messages

Use short, actionable format:
- `scanner: add SHA256 hashing for duplicate detection`
- `web: fix search filter for cliente dropdown`
- `database: add migration for new fip table`

### Schema Changes

When modifying database schema:
1. Update `minerva/database/models.py`
2. Add migration logic in `minerva/database/migrations.py`
3. Document changes in comments

## Development Notes

- **Python Version**: 3.10+
- **Database**: SQLite with FTS5 for full-text search
- **AI Backend**: Optional Ollama (local LLM) for automated classification
- **Web Framework**: Flask
- **No Tests Discovered**: No test harness or test commands found in repository

## Reference Documentation

For detailed information, consult:
- `PRD_Minerva_Dettaglio.md` - Authoritative product requirements
- `ISTRUZIONI_SCANNER.md` - Scanner usage guide
- `ISTRUZIONI_WEB.md` - Web interface guide
- `.github/copilot-instructions.md` - Existing AI agent instructions
