"""セッション・実行環境をまたいだ実データの引き継ぎ(export/import)。

config/profile.yaml・config/settings.yaml・data/autox.db(下書きキュー・分析
スナップショット)は個人情報のため.gitignore対象で、Git経由では一切運ばれない。
そのため会話コンテキストのリセット(/clear)や、別の実行環境(ローカル⇄クラウド、
複数デバイス)への引き継ぎでは、これらを1つのファイルにまとめて出力し、
次のセッションでそのまま復元できるようにする。

「これまでの経緯を要約する」のではなく「実データそのものを運ぶ」ことで、
要約の抜け漏れ(重複表現の見落とし・回答内容の欠落など)を構造的に防ぐのが狙い。
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .. import config, db

BUNDLE_VERSION = 1


def _load_settings_raw() -> dict[str, Any]:
    """example へのフォールバックはせず、settings.yaml自体の有無をそのまま反映する。"""
    path = config.settings_path()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def export_bundle() -> dict[str, Any]:
    """profile・settings・下書きキュー・分析スナップショットを1つのdictにまとめる。"""
    db.init_schema()
    with db.connect() as conn:
        posts = [dict(r) for r in conn.execute("SELECT * FROM posts ORDER BY id").fetchall()]
        snapshots = [
            dict(r) for r in conn.execute("SELECT * FROM snapshots ORDER BY date").fetchall()
        ]
    return {
        "version": BUNDLE_VERSION,
        "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
        "profile": config.load_profile(),
        "settings": _load_settings_raw(),
        "posts": posts,
        "snapshots": snapshots,
    }


def default_bundle_path() -> Path:
    return config.data_dir() / "handoff_bundle.yaml"


def write_bundle(out_path: Path | None = None) -> Path:
    out_path = out_path or default_bundle_path()
    config.ensure_data_dirs()
    bundle = export_bundle()
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(bundle, f, allow_unicode=True, sort_keys=False)
    return out_path


def read_bundle(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        raise ValueError(f"{path} は空か、読み込めませんでした。")
    return data


def existing_data_summary() -> tuple[int, int]:
    """import前チェック用: 現在DBにある posts / snapshots の件数。"""
    db.init_schema()
    with db.connect() as conn:
        posts_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        snapshots_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    return posts_count, snapshots_count


def import_bundle(data: dict[str, Any], force: bool = False) -> dict[str, int]:
    """bundleの内容でprofile.yaml・settings.yaml・DBを復元する。

    force=False で既存の posts/snapshots が1件でもあれば例外を出す
    (現在進行中の作業を誤って上書きしないためのガード)。
    """
    posts_count, snapshots_count = existing_data_summary()
    if not force and (posts_count or snapshots_count):
        raise RuntimeError(
            f"既存データがあります(下書き{posts_count}件・スナップショット{snapshots_count}件)。"
            "上書きするには --force を指定してください。"
        )

    if data.get("profile"):
        config.save_profile(data["profile"])

    if data.get("settings"):
        config.config_dir().mkdir(parents=True, exist_ok=True)
        with config.settings_path().open("w", encoding="utf-8") as f:
            yaml.safe_dump(data["settings"], f, allow_unicode=True, sort_keys=False)

    db.init_schema()
    with db.connect() as conn:
        conn.execute("DELETE FROM posts")
        conn.execute("DELETE FROM snapshots")
        for p in data.get("posts", []):
            conn.execute(
                "INSERT INTO posts "
                "(id, category, content, status, warning, created_at, scheduled_at, posted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    p["id"],
                    p["category"],
                    p["content"],
                    p["status"],
                    p.get("warning"),
                    p["created_at"],
                    p.get("scheduled_at"),
                    p.get("posted_at"),
                ),
            )
        for s in data.get("snapshots", []):
            conn.execute(
                "INSERT INTO snapshots "
                "(id, date, followers, likes, replies, impressions, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    s["id"],
                    s["date"],
                    s["followers"],
                    s["likes"],
                    s["replies"],
                    s["impressions"],
                    s["created_at"],
                ),
            )

    return {"posts": len(data.get("posts", [])), "snapshots": len(data.get("snapshots", []))}
