"""Bounded local memory and SQLite FTS knowledge, with no embedding model."""
import re
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, value TEXT)")
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge USING fts5(source, body)")

    def remember(self, value):
        value = value.strip()[:300]
        self.db.execute("INSERT INTO facts(value) VALUES (?)", (value,))
        self.db.execute("DELETE FROM facts WHERE id NOT IN (SELECT id FROM facts ORDER BY id DESC LIMIT 20)")
        self.db.commit()

    def facts(self):
        return [row[0] for row in self.db.execute("SELECT value FROM facts ORDER BY id DESC LIMIT 10")]

    def forget(self):
        self.db.execute("DELETE FROM facts")
        self.db.commit()

    def index(self, directory):
        self.db.execute("DELETE FROM knowledge")
        count = 0
        for path in sorted(Path(directory).glob("*")):
            if path.suffix.lower() not in {".txt", ".md"} or path.stat().st_size > 1000000:
                continue
            text = path.read_text(encoding="utf-8")
            for start in range(0, len(text), 900):
                self.db.execute("INSERT INTO knowledge VALUES (?, ?)", (path.name, text[start:start+1000]))
                count += 1
                if count >= 5000:
                    self.db.commit()
                    return count
        self.db.commit()
        return count

    def search(self, query):
        words = re.findall(r"[a-zA-Z0-9]{3,}", query)[:12]
        if not words:
            return []
        expression = " OR ".join(f'"{w}"' for w in words)
        rows = self.db.execute("SELECT source, body FROM knowledge WHERE knowledge MATCH ? ORDER BY rank LIMIT 2", (expression,))
        return [{"source": row[0], "text": row[1][:600]} for row in rows]

    def close(self):
        self.db.close()
