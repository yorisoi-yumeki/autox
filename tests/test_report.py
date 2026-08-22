import datetime as dt

from autox import config
from autox.analytics import report, tracker


def test_report_generation_with_no_data(isolated_env):
    path = report.generate_report()
    html = path.read_text(encoding="utf-8")
    assert "autox 分析レポート" in html
    assert "データがまだありません" in html


def test_elapsed_since_start_with_no_setting():
    assert report._elapsed_since_start(None) == "-"
    assert report._elapsed_since_start("") == "-"


def test_elapsed_since_start_computes_days_and_months():
    started = (dt.date.today() - dt.timedelta(days=95)).isoformat()
    label = report._elapsed_since_start(started)
    assert "95日" in label
    assert "3ヶ月" in label


def test_report_shows_elapsed_since_start(isolated_env):
    started = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    config.config_dir().mkdir(parents=True, exist_ok=True)
    (config.config_dir() / "settings.yaml").write_text(
        f'started_on: "{started}"\n', encoding="utf-8"
    )

    path = report.generate_report()
    html = path.read_text(encoding="utf-8")
    assert "運用開始からの経過" in html
    assert "10日" in html


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
