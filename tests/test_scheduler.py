import datetime as dt
import random

import pytest

from autox.content import queue
from autox.scheduling import scheduler

SETTINGS = {
    "golden_hour": {"start": "20:00", "end": "22:00"},
}


def test_random_time_in_window_stays_within_bounds():
    start, end = scheduler.golden_window(SETTINGS)
    rng = random.Random(1)
    for _ in range(200):
        t = scheduler.random_time_in_window(start, end, rng)
        assert (start.hour, start.minute) <= (t.hour, t.minute) <= (end.hour, end.minute)


def test_invalid_golden_window_raises():
    with pytest.raises(ValueError):
        scheduler.golden_window({"golden_hour": {"start": "22:00", "end": "20:00"}})


def test_schedule_pending_assigns_one_per_day_with_randomized_times(isolated_env):
    for i in range(5):
        pid = queue.add_draft("daily_life", f"投稿{i}")
        queue.approve(pid)

    assignments = scheduler.schedule_pending(
        start_date=dt.date(2026, 1, 1), seed=42, settings=SETTINGS
    )

    assert len(assignments) == 5
    dates = [when.date() for _, when in assignments]
    assert dates == [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(5)]

    for _, when in assignments:
        assert dt.time(20, 0) <= when.time() <= dt.time(22, 0)

    # 固定時刻に見えないよう、時刻がばらけていること
    times = {when.time() for _, when in assignments}
    assert len(times) > 1

    # DB側のステータスも更新されていること
    for post, when in assignments:
        stored = queue.get(post.id)
        assert stored.status == "scheduled"
        assert stored.scheduled_at == when.isoformat(timespec="minutes")


def test_schedule_pending_skips_dates_already_scheduled(isolated_env):
    taken_id = queue.add_draft("hobby", "既に予約済み")
    queue.approve(taken_id)
    queue.mark_scheduled(taken_id, dt.datetime(2026, 1, 1, 21, 0))

    new_id = queue.add_draft("hobby", "新規")
    queue.approve(new_id)

    assignments = scheduler.schedule_pending(
        start_date=dt.date(2026, 1, 1), seed=7, settings=SETTINGS
    )

    assert len(assignments) == 1
    post, when = assignments[0]
    assert post.id == new_id
    assert when.date() != dt.date(2026, 1, 1)
