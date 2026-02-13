"""Estrae la conversazione utente/assistente dai file JSONL di Claude Code.

Genera un file Markdown con i messaggi utente e le risposte conversazionali
dell'assistente, escludendo tool calls, tool results, e contenuti tecnici.

Uso:
    python tools/extract_chat.py                    # Solo messaggi utente
    python tools/extract_chat.py --all              # Conversazione completa (utente + assistente)
    python tools/extract_chat.py --last             # Solo l'ultima sessione
    python tools/extract_chat.py --session <uuid>   # Una sessione specifica
    python tools/extract_chat.py --output chat.md   # File di output personalizzato
    python tools/extract_chat.py --max-reply 1000   # Max caratteri per risposta (default: 2000)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Lunghezza max per le risposte assistant (troncamento)
DEFAULT_MAX_REPLY = 2000


def get_transcripts_dir() -> Path:
    """Determina automaticamente la cartella dei transcript per questo progetto."""
    # Ottieni il percorso assoluto del progetto (parent di tecdoc)
    # __file__ è in tools/, quindi parent.parent è tecdoc/, e parent.parent.parent è MINERVA/
    project_root = Path(__file__).parent.parent.parent.resolve()

    # Converti il path in un nome compatibile con la cartella .claude/projects
    # Es: e:\Sviluppo\Development\MINERVA -> e--Sviluppo-Development-MINERVA
    project_path_str = str(project_root)

    # Prima sostituisci ':' con '-', POI sostituisci '\' e '/' con '-'
    # Questo genera e:\... -> e-\... -> e--...
    project_name = project_path_str.replace(':', '-').replace('\\', '-').replace('/', '-')

    # La cartella dei transcript è in ~/.claude/projects/<project_name>
    transcripts_dir = Path.home() / ".claude" / "projects" / project_name

    return transcripts_dir


TRANSCRIPTS_DIR = get_transcripts_dir()


def find_sessions(transcripts_dir: Path) -> list[Path]:
    """Trova tutti i file JSONL delle sessioni principali (no subagents)."""
    sessions = []
    for f in transcripts_dir.glob("*.jsonl"):
        if f.parent == transcripts_dir:
            sessions.append(f)
    return sorted(sessions, key=lambda f: f.stat().st_mtime)


def extract_messages(
    jsonl_path: Path,
    include_assistant: bool = False,
    max_reply: int = DEFAULT_MAX_REPLY,
) -> list[dict]:
    """Estrae i messaggi conversazionali dal file JSONL.

    Per l'utente: estrae solo i messaggi digitati (no tool_result).
    Per l'assistente: estrae testo e thinking, esclude tool_use.
    Aggrega blocchi dello stesso requestId in un'unica risposta.

    Returns:
        Lista di dict con: role, text, timestamp, [thinking]
    """
    messages: list[dict] = []
    seen_user_texts: set[str] = set()

    # Per aggregare i blocchi assistant dello stesso requestId
    assistant_replies: dict[str, dict] = {}  # requestId -> {texts, thinkings, timestamp}

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            message = entry.get("message", {})
            role = message.get("role")
            content = message.get("content", [])

            # --- Messaggi utente ---
            if role == "user" and entry_type == "user":
                # Salta tool_result (risposte a tool_use dell'assistente)
                if isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content
                ):
                    continue

                text = _extract_user_text(content)
                if not text or text in seen_user_texts:
                    continue
                # Filtra context continuation summaries
                if text.startswith("This session is being continued from a previous conversation"):
                    continue
                seen_user_texts.add(text)

                # Prima di aggiungere il messaggio utente, flush eventuali
                # risposte assistant pendenti
                _flush_assistant_replies(
                    assistant_replies, messages, include_assistant, max_reply
                )

                messages.append({
                    "role": "user",
                    "text": text,
                    "timestamp": entry.get("timestamp", ""),
                })

            # --- Messaggi assistente ---
            elif role == "assistant" and entry_type == "assistant" and include_assistant:
                request_id = entry.get("requestId", "")
                if not request_id:
                    continue

                if request_id not in assistant_replies:
                    assistant_replies[request_id] = {
                        "texts": [],
                        "thinkings": [],
                        "timestamp": entry.get("timestamp", ""),
                    }

                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            text = block.get("text", "").strip()
                            if text:
                                assistant_replies[request_id]["texts"].append(text)
                        elif btype == "thinking":
                            thinking = block.get("thinking", "").strip()
                            if thinking:
                                assistant_replies[request_id]["thinkings"].append(thinking)
                        # tool_use -> ignorato

    # Flush risposte assistant rimanenti
    _flush_assistant_replies(assistant_replies, messages, include_assistant, max_reply)

    return messages


def _flush_assistant_replies(
    replies: dict[str, dict],
    messages: list[dict],
    include_assistant: bool,
    max_reply: int,
) -> None:
    """Converte le risposte assistant aggregate in messaggi e svuota il buffer."""
    if not include_assistant or not replies:
        return

    for request_id in sorted(replies, key=lambda k: replies[k]["timestamp"]):
        data = replies[request_id]
        text_parts = data["texts"]
        thinking_parts = data["thinkings"]

        # Combina solo il testo conversazionale (non i thinking interni brevi)
        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            continue

        # Tronca se troppo lungo
        if len(full_text) > max_reply:
            full_text = full_text[:max_reply] + "\n\n[... troncato]"

        msg: dict = {
            "role": "assistant",
            "text": full_text,
            "timestamp": data["timestamp"],
        }

        # Aggiungi thinking
        if thinking_parts:
            combined_thinking = "\n\n".join(thinking_parts)
            if len(combined_thinking) > max_reply:
                combined_thinking = combined_thinking[:max_reply] + "\n\n[... troncato]"
            msg["thinking"] = combined_thinking

        messages.append(msg)

    replies.clear()


def _extract_user_text(content) -> str:
    """Estrae il testo dal campo content di un messaggio utente."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return ""


def format_timestamp(ts: str) -> str:
    """Formatta un timestamp ISO in formato leggibile."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts


def generate_markdown(
    sessions_messages: list[tuple[Path, list[dict]]],
    include_assistant: bool = False,
) -> str:
    """Genera il contenuto Markdown."""
    lines = [
        "# Minerva - Cronologia Chat con Claude Code",
        "",
        f"> Estratto il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> Sessioni trovate: {len(sessions_messages)}",
    ]
    if include_assistant:
        lines.append("> Modalita': conversazione completa (utente + assistente)")
    else:
        lines.append("> Modalita': solo messaggi utente")
    lines += ["", "---", ""]

    for session_path, messages in sessions_messages:
        session_id = session_path.stem
        user_messages = [m for m in messages if m["role"] == "user"]

        if not user_messages:
            continue

        lines.append(f"## Sessione `{session_id[:8]}...`")
        lines.append(f"*Messaggi utente: {len(user_messages)}*")
        lines.append("")

        msg_num = 0
        for msg in messages:
            if msg["role"] == "user":
                msg_num += 1
                lines.append(f"### {msg_num}. Utente")
                lines.append("")
                # Usa blockquote per messaggi utente
                for uline in msg["text"].split("\n"):
                    lines.append(f"> {uline}")
                lines.append("")

            elif msg["role"] == "assistant" and include_assistant:
                lines.append("**Claude**:")
                lines.append("")
                # Testo risposta (senza thinking/ragionamento interno)
                lines.append(msg["text"])
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Estrae la conversazione dai transcript Claude Code"
    )
    # Default output in tools/chat.md
    default_output = Path(__file__).parent / "chat.md"
    parser.add_argument(
        "--output", "-o", default=str(default_output),
        help=f"File di output (default: {default_output})"
    )
    parser.add_argument(
        "--last", action="store_true", default=True,
        help="Solo l'ultima sessione (default: True)"
    )
    parser.add_argument(
        "--all-sessions", action="store_true",
        help="Tutte le sessioni (disabilita --last)"
    )
    parser.add_argument(
        "--session", "-s",
        help="UUID specifico della sessione"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", default=True,
        help="Includi anche le risposte conversazionali dell'assistente (default: True)"
    )
    parser.add_argument(
        "--user-only", action="store_true",
        help="Solo messaggi utente (disabilita --all)"
    )
    parser.add_argument(
        "--append", action="store_true", default=True,
        help="Appende al file esistente invece di sovrascrivere (default: True)"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Sovrascrive il file invece di appendere (disabilita --append)"
    )
    parser.add_argument(
        "--max-reply", type=int, default=DEFAULT_MAX_REPLY,
        help=f"Max caratteri per risposta assistant (default: {DEFAULT_MAX_REPLY})"
    )
    parser.add_argument(
        "--dir", "-d", default=str(TRANSCRIPTS_DIR),
        help="Cartella dei transcript"
    )
    args = parser.parse_args()

    # Se --user-only è specificato, disabilita --all
    if args.user_only:
        args.all = False

    # Se --all-sessions è specificato, disabilita --last
    if args.all_sessions:
        args.last = False

    # Se --overwrite è specificato, disabilita --append
    if args.overwrite:
        args.append = False

    transcripts_dir = Path(args.dir)
    if not transcripts_dir.exists():
        print(f"Cartella transcript non trovata: {transcripts_dir}", file=sys.stderr)
        sys.exit(1)

    if args.session:
        target = transcripts_dir / f"{args.session}.jsonl"
        if not target.exists():
            print(f"Sessione non trovata: {args.session}", file=sys.stderr)
            sys.exit(1)
        sessions = [target]
    else:
        sessions = find_sessions(transcripts_dir)
        if args.last and sessions:
            sessions = [sessions[-1]]

    if not sessions:
        print("Nessuna sessione trovata.", file=sys.stderr)
        sys.exit(1)

    sessions_messages = []
    for session_path in sessions:
        messages = extract_messages(
            session_path,
            include_assistant=args.all,
            max_reply=args.max_reply,
        )
        if messages:
            sessions_messages.append((session_path, messages))

    md = generate_markdown(sessions_messages, include_assistant=args.all)

    output_path = Path(args.output)

    # Modalità append: aggiungi al file esistente
    if args.append and output_path.exists():
        # Aggiungi separatore con timestamp
        separator = f"\n\n---\n\n## Aggiornamento del {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Estrai solo il contenuto delle sessioni (salta l'header iniziale del markdown)
        lines = md.split("\n")
        # Trova la prima riga "## Sessione" e prendi tutto da lì in poi
        session_start_idx = next(
            (i for i, line in enumerate(lines) if line.startswith("## Sessione")),
            0
        )
        new_content = "\n".join(lines[session_start_idx:])

        # Appende al file esistente
        with output_path.open("a", encoding="utf-8") as f:
            f.write(separator)
            f.write(new_content)

        print(f"Contenuto aggiunto in modalità incrementale")
    else:
        # Modalità overwrite: sostituisce il file
        output_path.write_text(md, encoding="utf-8")
        print(f"File sovrascritto")

    total_user = sum(
        len([m for m in msgs if m["role"] == "user"])
        for _, msgs in sessions_messages
    )
    total_assistant = sum(
        len([m for m in msgs if m["role"] == "assistant"])
        for _, msgs in sessions_messages
    )
    print(f"Estratti {total_user} messaggi utente e {total_assistant} risposte "
          f"da {len(sessions_messages)} sessioni")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
