# Copilot / AI Agent Instructions for Minerva repository

Purpose

- Help AI coding agents be immediately productive working on this repository by documenting discovered architecture, conventions, and concrete examples taken from the project's PRD.

What this repo contains (observed)

- Primary artifacts are product requirements and design docs (example: `PRD_Minerva_Dettaglio.md`).
- The PRD defines an intended Python project layout under a `minerva/` package (scanner, database, web, utils) and uses Python 3.10+, SQLite and a local Ollama AI.

Key architecture & patterns (from PRD)

- Two macro-components share a single SQLite DB: the batch Scanner/Analyzer and the Web UI (Flask/Streamlit). See PRD sections "Architettura del Sistema" and "Componente 1/2" for flow diagrams.
- Canonical unique key: `percorso_relativo` (do NOT rely on absolute network paths). Use `percorso_base` + `percorso_relativo` when presenting a full path.
- Client-specific opt-in: a `censimento_filtro.json` file located in a client root enables scanning for that client. If absent, the client is skipped.
- File identity is content-hash based: scanner computes a SHA-256 (`documento_hash`) and records it in the `documenti` table to detect MOD/DUP/SPO/CAN states.

Files / modules referenced in PRD (use as anchors)

- `minerva/config/settings.py` — global settings (paths, DB location, scheduling).
- `minerva/scanner/directory_walker.py` — enumerates filesystem using `censimento_filtro.json` rules.
- `minerva/scanner/ai_classifier.py` — integrates with Ollama for automated classification.
- `minerva/database/models.py` and `repository.py` — DB schema and CRUD (SQLite).
- `main_scanner.py` and `main_web.py` — intended entrypoints for batch and web components.

Agent behavior: what to do first

- Read `PRD_Minerva_Dettaglio.md` to understand flows before proposing code changes; the PRD is the authoritative spec in this repo.
- If you need to run or test code, ask the human which of these exist in the workspace: runnable Python packages, a `requirements.txt`/`pyproject.toml`, and any Docker/virtualenv setup. No build or test scripts were discovered in the repo root.
- When editing code or docs, preserve Italian domain vocabulary used in the PRD (e.g. `percorso_relativo`, `censimento_filtro.json`, `documento_hash`, `cliente_cartella`).

Concrete editing rules and examples

- When adding scanner logic, enforce the "opt-in" rule: skip a client if `censimento_filtro.json` is missing in the client's root.
- Use SHA-256 for content hashing and store as `documento_hash` (PRD enumerates why and how the hash is used). Implement hash comparisons to detect MOD/DUP/SPO flow exactly as described.
- Implement classification so that manual overrides are never overwritten by automatic scans (PRD: Manual > Automatic). Only update DB fields that are NULL during scans.

Conventions for commits and diffs

- Keep commit messages short and actionable: `scanner: add SHA256 hashing + document_hash storage` or `docs: clarify censimento_filtro.json opt-in behavior in README`.
- When changing schema, include a migration script under `minerva/database/migrations.py` and a short note in the PRD/README.

When unsure, ask these specific questions

- Where are the runnable code files (if any) and how do you run them locally (python command, venv, Docker)?
- Where should I put integration tests or how do you want test harnesses executed? (there are no test commands discovered)
- Do you prefer Italian or English for inline code comments and commit messages? (PRD is in Italian; default to Italian unless told otherwise)

Limitations

- This instruction file is derived from `PRD_Minerva_Dettaglio.md` and the repository snapshot; it documents only patterns explicitly present in discovered files. If there are hidden modules, pipelines, or CI scripts elsewhere, request their paths before implementing runtime changes.

Feedback

- If any section is unclear or you want more granular agent rules (linting, tests, CI), tell me which area to expand and I will update this file.
