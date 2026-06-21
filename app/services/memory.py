from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from time import time


class ConversationMemory:
    def __init__(self, db_path: str = "./data/myscholar.db") -> None:
        self.db_path = Path(db_path.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", ""))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def add_message(self, session_id: str, role: str, content: str, madhab: str = "general") -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, madhab, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, madhab, time()),
            )
            conn.commit()

    def get_recent(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, madhab FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        rows.reverse()
        return [{"role": r[0], "content": r[1], "madhab": r[2]} for r in rows]

    def clear(self, session_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()

    def list_sessions(self) -> list[str]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT session_id FROM messages ORDER BY MAX(created_at) DESC LIMIT 20"
            ).fetchall()
        return [r[0] for r in rows]

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    madhab TEXT NOT NULL DEFAULT 'general',
                    created_at REAL NOT NULL
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id, id)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
