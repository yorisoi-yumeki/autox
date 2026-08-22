"""投稿下書きキューのCRUD(SQLite: postsテーブル)。

ステータス遷移: draft -> approved -> scheduled -> posted
                draft -> rejected
承認(approved)されたものだけが scheduling/scheduler.py の対象になる。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .. import db


@dataclass
class Post:
    id: int
    category: str
    content: str
    status: str
    warning: str | None
    created_at: str
    scheduled_at: str | None
    posted_at: str | None

    @classmethod
    def from_row(cls, row) -> "Post":
        return cls(
            id=row["id"],
            category=row["category"],
            content=row["content"],
            status=row["status"],
            warning=row["warning"],
            created_at=row["created_at"],
            scheduled_at=row["scheduled_at"],
            posted_at=row["posted_at"],
        )


def add_draft(category: str, content: str, warning: str | None = None) -> int:
    db.init_schema()
    now = dt.datetime.now().isoformat(timespec="seconds")
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO posts (category, content, status, warning, created_at) "
            "VALUES (?, ?, 'draft', ?, ?)",
            (category, content, warning, now),
        )
        return cur.lastrowid


def list_posts(status: str | None = None) -> list[Post]:
    db.init_schema()
    with db.connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM posts ORDER BY id").fetchall()
    return [Post.from_row(r) for r in rows]


def get(post_id: int) -> Post | None:
    db.init_schema()
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return Post.from_row(row) if row else None


def set_status(post_id: int, status: str, **fields) -> None:
    db.init_schema()
    assignments = ["status = ?"]
    values: list = [status]
    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        values.append(value)
    values.append(post_id)
    with db.connect() as conn:
        conn.execute(
            f"UPDATE posts SET {', '.join(assignments)} WHERE id = ?", values
        )


def approve(post_id: int) -> None:
    set_status(post_id, "approved")


def reject(post_id: int) -> None:
    set_status(post_id, "rejected")


def mark_scheduled(post_id: int, scheduled_at: dt.datetime) -> None:
    set_status(post_id, "scheduled", scheduled_at=scheduled_at.isoformat(timespec="minutes"))


def mark_posted(post_id: int) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    set_status(post_id, "posted", posted_at=now)
