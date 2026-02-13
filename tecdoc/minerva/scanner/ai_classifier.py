"""Integrazione con Ollama per classificazione AI dei documenti."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """Sei un assistente specializzato nella classificazione di documenti tecnici aziendali \
nel settore manifatturiero (MES, APS, ERP). Analizza il seguente testo estratto da un documento e restituisci:

1. Una lista di parole chiave rilevanti (max 20)
2. Un breve riassunto del contenuto (max 200 parole)
3. Le aree tematiche probabili tra: OPM, MES, APS, INT, IND, KPI
4. Il tipo documento probabile tra: SC, SS, TS, MU, CU, NU, GA, AV, SV, TB, CR, AP, MN

Testo:
{testo}

Rispondi SOLO in formato JSON valido:
{{"parole_chiave": [...], "riassunto": "...", "aree_suggerite": [...], "tipo_documento_suggerito": "..."}}"""


def classify_document(
    testo: str,
    base_url: str = "http://localhost:11434",
    model: str = "llama3",
    timeout: int = 120,
    max_chars: int = 100000,
    filename: str = "",
) -> dict[str, Any] | None:
    """Invia il testo del documento a Ollama per la classificazione.

    Args:
        testo: Testo del documento da classificare.
        base_url: URL di Ollama.
        model: Modello Ollama da usare.
        timeout: Timeout in secondi.
        max_chars: Massimo numero di caratteri da inviare.
        filename: Nome del file (per logging).

    Returns:
        Dizionario con i risultati della classificazione, o None in caso di errore.
    """
    if not testo or not testo.strip():
        return None

    # Tronca il testo se necessario
    testo_troncato = testo[:max_chars]

    prompt = CLASSIFICATION_PROMPT.format(testo=testo_troncato)

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=timeout,
        )
        response.raise_for_status()

        data = response.json()
        raw_response = data.get("response", "")

        # Prova a parsare il JSON dalla risposta
        return _parse_ai_response(raw_response, filename)

    except requests.ConnectionError:
        logger.warning("[%s] Ollama non raggiungibile a %s", filename, base_url)
        return None
    except requests.Timeout:
        logger.warning("[%s] Timeout Ollama dopo %d secondi", filename, timeout)
        return None
    except requests.RequestException as e:
        logger.warning("[%s] Errore chiamata Ollama: %s", filename, e)
        return None


def _parse_ai_response(raw: str, filename: str = "") -> dict[str, Any] | None:
    """Prova a parsare la risposta JSON da Ollama."""
    # Pulisci la risposta rimuovendo markdown code blocks
    cleaned = raw.strip()

    # Cerca e rimuovi blocchi markdown ```json ... ``` o ``` ... ```
    # Gestisce anche testo introduttivo prima del blocco
    if "```" in cleaned:
        # Trova l'inizio del blocco markdown
        start_marker = cleaned.find("```")
        # Salta la prima riga (```json o ```)
        first_newline = cleaned.find("\n", start_marker)
        if first_newline > 0:
            cleaned = cleaned[first_newline + 1:]
        else:
            cleaned = cleaned[start_marker + 3:]

        # Rimuovi ``` finali se presenti
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()

    # Prima prova il parsing diretto
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Cerca un blocco JSON nella risposta
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            json_str = cleaned[start:end]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    logger.warning("[%s] Impossibile parsare risposta Ollama: %s...", filename, raw[:200])
    return None


def check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Verifica se Ollama è raggiungibile."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False
