"""Test directory walking and hash computation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from minerva.config.settings import load_config
from minerva.scanner.directory_walker import walk_client_directory
from minerva.scanner.file_hasher import compute_hash

def main():
    config = load_config()
    base_path = Path(config.percorsi_base[0].percorso)
    client_dir = base_path / "TECDOC"

    print(f"Scansione: {client_dir}")

    # Prepare filter
    filtro = {
        "directory_da_leggere": ["/*"],
        "directory_da_evitare": [],
        "formati_da_leggere": config.scanner.filtro_globale_default.formati_da_leggere,
        "filtro_data": config.scanner.filtro_globale_default.filtro_data,
    }

    print("Walking directory...")
    files = walk_client_directory(client_dir, filtro, config.scanner.file_esclusi_regex)
    print(f"Trovati {len(files)} file")

    # Try to hash first 10 files
    print("\nCalcolo hash primi 10 file:")
    for i, f in enumerate(files[:10]):
        print(f"{i+1}. {f.name}... ", end="", flush=True)
        try:
            h = compute_hash(f)
            print(f"OK ({h[:16]}...)")
        except Exception as e:
            print(f"ERRORE: {e}")

    print("\nTest completato!")

if __name__ == "__main__":
    main()
