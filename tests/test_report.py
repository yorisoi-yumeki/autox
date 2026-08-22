import datetime as dt

from autox.analytics import report, tracker


def test_report_generation_with_no_data(isolated_env):
    path = report.generate_report()
    html = path.read_text(encoding="utf-8")
    assert "autox 分析レポート" in html
    assert "データがまだありません" in html


def test_report_generation_with_snapshots(isolated_env):
    base = dt.date(2026, 1, 1)
    tracker.log_snapshot(followers=100, likes=10, replies=2, impressions=1000, date=base)
    tracker.log_snapshot(
        followers=105, likes=25, replies=5, impressions=1500, date=base + dt.timedelta(days=1)
    )
    tracker.log_snapshot(
        followers=112, likes=40, replies=9, impressions=2200, date=base + dt.timedelta(days=2)
    )

    path = report.generate_report()
    html = path.read_text(encoding="utf-8")

    assert "<svg" in html
    assert "+12" in html  # フォロワー増減(112-100)


def test_log_snapshot_upserts_same_date(isolated_env):
    d = dt.date(2026, 2, 1)
    tracker.log_snapshot(followers=50, likes=1, replies=0, impressions=100, date=d)
    tracker.log_snapshot(followers=60, likes=2, replies=1, impressions=200, date=d)

    snapshots = tracker.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0]["followers"] == 60
