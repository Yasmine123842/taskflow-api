"""Accès à la base SQLite."""

import os
import sqlite3
from collections.abc import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'a_faire',
    priority    TEXT NOT NULL DEFAULT 'moyenne',
    due_date    TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
"""


def db_path() -> str:
    """Chemin du fichier de base, configurable par variable d'environnement."""
    return os.environ.get("TASKFLOW_DB", "taskflow.db")


def connect() -> sqlite3.Connection:
    # check_same_thread=False : FastAPI peut ouvrir et fermer la connexion
    # dans des threads différents au cours d'une même requête.
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Dépendance FastAPI : une connexion par requête, toujours refermée."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
