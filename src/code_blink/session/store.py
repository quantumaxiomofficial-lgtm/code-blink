import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from code_blink.config.defaults import SESSIONS_DIR


def _get_db() -> sqlite3.Connection:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    db_path = SESSIONS_DIR / "sessions.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            updated_at TEXT,
            model TEXT,
            provider_url TEXT,
            title TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            tool_calls TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    return conn


class SessionStore:
    def __init__(self):
        self.conn = _get_db()
        self.current_session_id: Optional[str] = None

    def create_session(self, model: str, provider_url: str) -> str:
        import uuid
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO sessions (id, created_at, updated_at, model, provider_url) VALUES (?, ?, ?, ?, ?)",
            (session_id, now, now, model, provider_url),
        )
        self.conn.commit()
        self.current_session_id = session_id
        return session_id

    def save_message(self, role: str, content: str, tool_calls: list | None = None):
        if not self.current_session_id:
            return
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?)",
            (self.current_session_id, role, content, json.dumps(tool_calls) if tool_calls else None, now),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, self.current_session_id),
        )
        self.conn.commit()

    def get_history(self, session_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_sessions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, created_at, model, title FROM sessions ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
