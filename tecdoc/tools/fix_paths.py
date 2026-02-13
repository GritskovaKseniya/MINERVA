"""Fix percorso_base in database to match current configuration."""
import sqlite3
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.config.settings import load_config

def main():
    config = load_config()
    db_path = config.database.path

    # Get the current percorso_base from config
    new_base = None
    for percorso in config.percorsi_base:
        if percorso.nome == "TecDoc":
            new_base = percorso.percorso
            break

    if not new_base:
        print("Errore: percorso TecDoc non trovato nella configurazione")
        return

    print(f"Nuovo percorso base: {new_base}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check current paths
    cur.execute("SELECT DISTINCT percorso_base FROM documenti")
    old_paths = [row[0] for row in cur.fetchall()]
    print(f"\nPercorsi base attuali nel DB:")
    for path in old_paths:
        print(f"  - {path}")

    # Count documents
    cur.execute("SELECT COUNT(*) FROM documenti")
    total = cur.fetchone()[0]
    print(f"\nTotale documenti: {total}")

    # Update all percorso_base
    print(f"\nAggiornamento percorsi base a: {new_base}")
    cur.execute("UPDATE documenti SET percorso_base = ?", (new_base,))
    updated = cur.rowcount

    conn.commit()
    conn.close()

    print(f"✓ Aggiornati {updated} documenti")

if __name__ == "__main__":
    main()
