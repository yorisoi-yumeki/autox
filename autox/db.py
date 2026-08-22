"""SQLiteの接続とスキーマ初期化(下書きキュー・分析スナップショット用)。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',   -- draft / approved / rejected / scheduled / posted
    warning TEXT,                            -- generator.pyの整合性チェックで疑わしい場合のメモ
    created_at TEXT NOT NULL,
    scheduled_at TEXT,
    posted_at TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,   -- YYYY-MM-DD
    followers INTEGER NOT NULL,
    likes INTEGER NOT NULL,
    replies INTEGER NOT NULL,
    impressions INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.ensure_data_dirs()
    conn = sqlite3.connect(config.db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
