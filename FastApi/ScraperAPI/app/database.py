from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from app.config import get_settings


def get_database_path() -> Path:
    settings = get_settings()
    return settings.database_path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS researches (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                markdown_report TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                research_id TEXT,
                url TEXT NOT NULL,
                title TEXT,
                status_code INTEGER,
                content_type TEXT,
                fetched_at TEXT NOT NULL,
                extraction_json TEXT NOT NULL,
                FOREIGN KEY (research_id) REFERENCES researches(id)
            )
            """
        )
