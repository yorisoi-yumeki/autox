"""日次スナップショット(フォロワー数・いいね・返信・インプレッション)の記録。

X APIに未接続なので、X純正のアナリティクス画面(または目視)から
手入力することを想定している。同じ日付で再度logすれば上書きされる。
"""

from __future__ import annotations

import datetime as dt

from .. import db


def log_snapshot(
    followers: int,
    likes: int,
    replies: int,
    impressions: int,
    date: dt.date | None = None,
) -> None:
    db.init_schema()
    date = date or dt.date.today()
    now = dt.datetime.now().isoformat(timespec="seconds")
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO snapshots (date, followers, likes, replies, impressions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                followers = excluded.followers,
                likes = excluded.likes,
                replies = excluded.replies,
                impressions = excluded.impressions,
                created_at = excluded.created_at
            """,
            (date.isoformat(), followers, likes, replies, impressions, now),
        )


def list_snapshots() -> list[dict]:
    db.init_schema()
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM snapshots ORDER BY date").fetchall()
    return [dict(r) for r in rows]
