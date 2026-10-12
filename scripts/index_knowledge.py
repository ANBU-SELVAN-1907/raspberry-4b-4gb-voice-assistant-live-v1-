import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.store import Store

store = Store(ROOT / "data/memory.sqlite3")
try:
    count = store.index(ROOT / "data/knowledge")
    print(f"Indexed {count} chunks. Knowledge stays entirely local.")
finally:
    store.close()
