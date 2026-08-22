from autox.content import queue


def test_add_and_list_draft(isolated_env):
    post_id = queue.add_draft("relationship_values", "テスト投稿です")
    posts = queue.list_posts(status="draft")
    assert len(posts) == 1
    assert posts[0].id == post_id
    assert posts[0].content == "テスト投稿です"
    assert posts[0].status == "draft"


def test_approve_and_reject(isolated_env):
    id1 = queue.add_draft("daily_life", "1件目")
    id2 = queue.add_draft("daily_life", "2件目")

    queue.approve(id1)
    queue.reject(id2)

    assert queue.get(id1).status == "approved"
    assert queue.get(id2).status == "rejected"
    assert [p.id for p in queue.list_posts(status="approved")] == [id1]
    assert [p.id for p in queue.list_posts(status="rejected")] == [id2]


def test_mark_scheduled_and_posted(isolated_env):
    import datetime as dt

    post_id = queue.add_draft("hobby", "予約テスト")
    queue.approve(post_id)

    when = dt.datetime(2026, 1, 1, 21, 0)
    queue.mark_scheduled(post_id, when)
    post = queue.get(post_id)
    assert post.status == "scheduled"
    assert post.scheduled_at.startswith("2026-01-01T21:00")

    queue.mark_posted(post_id)
    assert queue.get(post_id).status == "posted"
    assert queue.get(post_id).posted_at is not None
