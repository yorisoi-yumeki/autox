"""承認済み下書きを「ゴールデンタイム帯・ランダム時刻」で予約カレンダーに割り当てる。

実際の投稿は自動化せず、本人が手動で行う前提のツールなので、ここでの
ランダム化は「Xの自動化を機械的に見せないため」の仕掛けではない。
単に、毎日判で押したように同じ分(例: 20:00ちょうど)を狙うより、
ゴールデンタイム帯(デフォルト20:00-22:00)の中で「今日は何時頃投稿しよう」
という目安を都度示すことで、投稿し忘れを防ぎつつ自然な運用がしやすくなる、
というだけの目的。
このモジュールは実際の投稿は一切行わない。カレンダーを作るだけ。
"""

from __future__ import annotations

import csv
import datetime as dt
import random
from pathlib import Path
from typing import Any, Iterable

from .. import config
from ..content import queue


def _parse_hhmm(value: str) -> dt.time:
    hour, minute = value.split(":")
    return dt.time(int(hour), int(minute))


def golden_window(settings: dict[str, Any]) -> tuple[dt.time, dt.time]:
    gh = settings.get("golden_hour") or {}
    start = _parse_hhmm(gh.get("start", "20:00"))
    end = _parse_hhmm(gh.get("end", "22:00"))
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if end_minutes <= start_minutes:
        raise ValueError("golden_hour の end は start より後の時刻にしてください。")
    return start, end


def random_time_in_window(start: dt.time, end: dt.time, rng: random.Random) -> dt.time:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    chosen = rng.randint(start_minutes, end_minutes)
    return dt.time(chosen // 60, chosen % 60)


def existing_scheduled_dates() -> set[dt.date]:
    dates = set()
    for post in queue.list_posts(status="scheduled"):
        if post.scheduled_at:
            dates.add(dt.datetime.fromisoformat(post.scheduled_at).date())
    return dates


def schedule_pending(
    start_date: dt.date | None = None,
    seed: int | None = None,
    settings: dict[str, Any] | None = None,
) -> list[tuple[queue.Post, dt.datetime]]:
    """approved状態の下書きを1日1件ずつ、直近の空いている日から順に、
    ゴールデンタイム帯内のランダムな時刻へ割り当てる。

    副作用: 対象の投稿のステータスを scheduled に更新し、scheduled_at を記録する。
    実際にXへ投稿する処理はここには含まれない。
    """
    settings = settings if settings is not None else config.load_settings()
    start, end = golden_window(settings)
    rng = random.Random(seed)

    pending = queue.list_posts(status="approved")
    used_dates = existing_scheduled_dates()
    current_date = start_date or dt.date.today()

    assignments: list[tuple[queue.Post, dt.datetime]] = []
    for post in pending:
        while current_date in used_dates:
            current_date += dt.timedelta(days=1)
        chosen_time = random_time_in_window(start, end, rng)
        scheduled_at = dt.datetime.combine(current_date, chosen_time)
        queue.mark_scheduled(post.id, scheduled_at)
        assignments.append((post, scheduled_at))
        used_dates.add(current_date)
        current_date += dt.timedelta(days=1)

    return assignments


def export_calendar_csv(
    assignments: Iterable[tuple[queue.Post, dt.datetime]],
    out_path: Path | None = None,
) -> Path:
    out_path = out_path or (config.data_dir() / "post_calendar.csv")
    config.ensure_data_dirs()
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["scheduled_at", "category", "content"])
        for post, scheduled_at in assignments:
            writer.writerow(
                [scheduled_at.isoformat(timespec="minutes"), post.category, post.content]
            )
    return out_path
