"""日次スナップショットから、フォロワー推移・エンゲージメント率・
カテゴリ別/曜日別の傾向をまとめた自己完結HTMLレポートを生成する。

外部ライブラリ・外部CDNには依存しない(インラインSVGのみ)。
生成物はそのままブラウザで開けるほか、Artifactとして共有することもできる。
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Any

from .. import config
from ..content import queue
from . import tracker

WEEKDAY_LABELS_JA = ["月", "火", "水", "木", "金", "土", "日"]


def _compute_daily_deltas(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """前日比の差分とエンゲージメント率を計算する。先頭日は差分なし。"""
    rows = []
    prev = None
    for snap in snapshots:
        date = dt.date.fromisoformat(snap["date"])
        row = {"date": date, "followers": snap["followers"]}
        if prev is not None:
            d_likes = snap["likes"] - prev["likes"]
            d_replies = snap["replies"] - prev["replies"]
            d_impr = snap["impressions"] - prev["impressions"]
            row["delta_followers"] = snap["followers"] - prev["followers"]
            row["delta_engagement"] = d_likes + d_replies
            row["delta_impressions"] = d_impr
            row["engagement_rate"] = (d_likes + d_replies) / d_impr if d_impr > 0 else None
        else:
            row["delta_followers"] = None
            row["engagement_rate"] = None
        rows.append(row)
        prev = snap
    return rows


def _posts_by_date() -> dict[dt.date, list[queue.Post]]:
    posted = queue.list_posts(status="posted")
    grouped: dict[dt.date, list[queue.Post]] = {}
    for post in posted:
        if not post.posted_at:
            continue
        date = dt.datetime.fromisoformat(post.posted_at).date()
        grouped.setdefault(date, []).append(post)
    return grouped


def _category_averages(daily: list[dict[str, Any]], posts_by_date: dict[dt.date, list[queue.Post]]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for row in daily:
        rate = row.get("engagement_rate")
        if rate is None:
            continue
        posts = posts_by_date.get(row["date"], [])
        categories = {p.category for p in posts}
        if len(categories) == 1:
            buckets.setdefault(next(iter(categories)), []).append(rate)
    return {cat: sum(vals) / len(vals) for cat, vals in buckets.items()}


def _weekday_averages(daily: list[dict[str, Any]]) -> dict[int, float]:
    buckets: dict[int, list[float]] = {}
    for row in daily:
        rate = row.get("engagement_rate")
        if rate is None:
            continue
        buckets.setdefault(row["date"].weekday(), []).append(rate)
    return {wd: sum(vals) / len(vals) for wd, vals in buckets.items()}


def _svg_line_chart(points: list[tuple[str, float]], width: int = 640, height: int = 220) -> str:
    if not points:
        return "<p class='empty'>データがまだありません。</p>"
    pad = 32
    values = [v for _, v in points]
    v_min, v_max = min(values), max(values)
    if v_max == v_min:
        v_max += 1
    n = len(points)
    step = (width - 2 * pad) / max(n - 1, 1)

    def x(i: int) -> float:
        return pad + i * step

    def y(v: float) -> float:
        return height - pad - (v - v_min) / (v_max - v_min) * (height - 2 * pad)

    path_d = " ".join(
        f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(points)
    )
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="3" class="dot"><title>{html.escape(label)}: {v:g}</title></circle>'
        for i, (label, v) in enumerate(points)
    )
    first_label = html.escape(points[0][0])
    last_label = html.escape(points[-1][0])
    return f"""
<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="推移グラフ">
  <path d="{path_d}" class="line" fill="none" />
  {dots}
  <text x="{pad}" y="{height - 8}" class="axis-label">{first_label}</text>
  <text x="{width - pad}" y="{height - 8}" class="axis-label" text-anchor="end">{last_label}</text>
</svg>
"""


def _svg_bar_chart(items: list[tuple[str, float]], width: int = 640, height: int = 220) -> str:
    if not items:
        return "<p class='empty'>データがまだありません。</p>"
    pad = 32
    max_v = max(v for _, v in items) or 1
    n = len(items)
    slot = (width - 2 * pad) / n
    bar_w = slot * 0.6
    bars = []
    for i, (label, v) in enumerate(items):
        bar_h = (height - 2 * pad) * (v / max_v) if max_v else 0
        bx = pad + i * slot + (slot - bar_w) / 2
        by = height - pad - bar_h
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" class="bar">'
            f"<title>{html.escape(label)}: {v:.3f}</title></rect>"
        )
        bars.append(
            f'<text x="{bx + bar_w / 2:.1f}" y="{height - 8}" class="axis-label" text-anchor="middle">{html.escape(label)}</text>'
        )
    return f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="比較グラフ">{"".join(bars)}</svg>'


_HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>autox 分析レポート</title>
<style>
  :root {{
    --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280;
    --accent: #2563eb; --card-bg: #f8fafc; --border: #e2e8f0;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1115; --fg: #e5e7eb; --muted: #9ca3af;
      --accent: #60a5fa; --card-bg: #171a21; --border: #262b36;
    }}
  }}
  body {{ background: var(--bg); color: var(--fg); font-family: -apple-system, "Hiragino Sans", sans-serif;
         margin: 0; padding: 24px; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.05rem; margin-top: 2rem; color: var(--fg); }}
  .meta {{ color: var(--muted); font-size: 0.85rem; }}
  .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px;
          padding: 16px; margin-top: 12px; }}
  .chart {{ width: 100%; height: auto; overflow: visible; }}
  .line {{ stroke: var(--accent); stroke-width: 2; }}
  .dot {{ fill: var(--accent); }}
  .bar {{ fill: var(--accent); }}
  .axis-label {{ fill: var(--muted); font-size: 11px; }}
  .empty {{ color: var(--muted); }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
  .stat {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }}
  .stat .label {{ color: var(--muted); font-size: 0.8rem; }}
  .stat .value {{ font-size: 1.4rem; font-weight: 600; }}
</style>
</head>
<body>
<h1>autox 分析レポート</h1>
<p class="meta">生成日時: {generated_at} / 対象期間: {period}</p>

<div class="summary-grid">
  <div class="stat"><div class="label">フォロワー増減(期間累計)</div><div class="value">{follower_delta}</div></div>
  <div class="stat"><div class="label">平均エンゲージメント率</div><div class="value">{avg_engagement}</div></div>
  <div class="stat"><div class="label">記録日数</div><div class="value">{days_logged}</div></div>
</div>

<h2>フォロワー推移</h2>
<div class="card">{followers_chart}</div>

<h2>日次エンゲージメント率((いいね+返信)/インプレッション)</h2>
<div class="card">{engagement_chart}</div>

<h2>投稿カテゴリ別の平均エンゲージメント率</h2>
<div class="card">{category_chart}</div>
<p class="meta">同じ日に複数カテゴリを投稿した日は集計から除外しています(どのカテゴリの効果か切り分けられないため)。</p>

<h2>曜日別の平均エンゲージメント率</h2>
<div class="card">{weekday_chart}</div>

</body>
</html>
"""


def generate_report(out_path: Path | None = None) -> Path:
    snapshots = tracker.list_snapshots()
    daily = _compute_daily_deltas(snapshots)
    posts_by_date = _posts_by_date()

    followers_points = [(row["date"].isoformat(), row["followers"]) for row in daily]
    engagement_points = [
        (row["date"].isoformat(), row["engagement_rate"])
        for row in daily
        if row.get("engagement_rate") is not None
    ]
    category_avgs = _category_averages(daily, posts_by_date)
    weekday_avgs = _weekday_averages(daily)
    weekday_items = [
        (WEEKDAY_LABELS_JA[wd], weekday_avgs[wd]) for wd in sorted(weekday_avgs)
    ]

    if len(daily) >= 2:
        follower_delta = daily[-1]["followers"] - daily[0]["followers"]
        follower_delta_str = f"{follower_delta:+d}"
        period = f"{daily[0]['date'].isoformat()} 〜 {daily[-1]['date'].isoformat()}"
    else:
        follower_delta_str = "-"
        period = daily[0]["date"].isoformat() if daily else "データなし"

    rates = [r for r in (row.get("engagement_rate") for row in daily) if r is not None]
    avg_engagement_str = f"{(sum(rates) / len(rates)):.2%}" if rates else "-"

    html_out = _HTML_TEMPLATE.format(
        generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        period=period,
        follower_delta=follower_delta_str,
        avg_engagement=avg_engagement_str,
        days_logged=len(daily),
        followers_chart=_svg_line_chart(followers_points),
        engagement_chart=_svg_line_chart(
            [(d, r) for d, r in engagement_points]
        ),
        category_chart=_svg_bar_chart(sorted(category_avgs.items())),
        weekday_chart=_svg_bar_chart(weekday_items),
    )

    config.ensure_data_dirs()
    out_path = out_path or (config.reports_dir() / f"report_{dt.date.today().strftime('%Y%m%d')}.html")
    out_path.write_text(html_out, encoding="utf-8")
    return out_path
