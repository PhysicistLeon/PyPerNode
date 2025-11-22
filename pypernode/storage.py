from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Tuple


class NodeStorage:
    """Persist node definitions to a local SQLite database."""

    def __init__(self, path: Optional[Path] = None):
        self.db_path = path or Path(__file__).resolve().parent / "nodes.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS node_definitions (
                    name TEXT PRIMARY KEY,
                    code TEXT NOT NULL
                )
                """
            )

    def fetch_all(self) -> Iterable[Tuple[str, str]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT name, code FROM node_definitions")
            return cur.fetchall()

    def get(self, name: str) -> Optional[str]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT code FROM node_definitions WHERE name = ?", (name,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def exists(self, name: str) -> bool:
        return self.get(name) is not None

    def upsert(self, name: str, code: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO node_definitions (name, code) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET code = excluded.code
                """,
                (name, code),
            )
