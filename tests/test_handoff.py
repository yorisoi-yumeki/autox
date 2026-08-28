import pytest

from autox import config, handoff
from autox.analytics import tracker
from autox.content import queue


def test_export_bundle_contains_profile_settings_and_posts(isolated_env):
    config.save_profile({"q1": "回答A"})
    settings_path = config.config_dir() / "settings.yaml"
    settings_path.write_text("golden_hour:\n  start: '20:00'\n  end: '22:00'\n", encoding="utf-8")

    post_id = queue.add_draft("daily_life", "テスト投稿")
    tracker.log_snapshot(followers=10, likes=1, replies=2, impressions=100)

    bundle = handoff.export_bundle()

    assert bundle["profile"] == {"q1": "回答A"}
    assert bundle["settings"]["golden_hour"]["start"] == "20:00"
    assert [p["id"] for p in bundle["posts"]] == [post_id]
    assert bundle["posts"][0]["content"] == "テスト投稿"
    assert len(bundle["snapshots"]) == 1


def test_write_and_import_bundle_round_trip(isolated_env, tmp_path):
    config.save_profile({"q1": "回答A"})
    id1 = queue.add_draft("daily_life", "1件目")
    queue.approve(id1)

    out_path = handoff.write_bundle(tmp_path / "bundle.yaml")
    assert out_path.exists()

    # 別環境を模して config/data を初期化し直す
    other_config = tmp_path / "other_config"
    other_data = tmp_path / "other_data"
    other_config.mkdir()
    other_data.mkdir()
    import os

    os.environ["AUTOX_CONFIG_DIR"] = str(other_config)
    os.environ["AUTOX_DATA_DIR"] = str(other_data)

    data = handoff.read_bundle(out_path)
    counts = handoff.import_bundle(data)

    assert counts["posts"] == 1
    restored = queue.get(id1)
    assert restored is not None
    assert restored.content == "1件目"
    assert restored.status == "approved"
    assert config.load_profile() == {"q1": "回答A"}


def test_import_bundle_refuses_to_overwrite_without_force(isolated_env, tmp_path):
    queue.add_draft("daily_life", "既存の下書き")
    bundle = {"version": 1, "profile": {}, "settings": {}, "posts": [], "snapshots": []}

    with pytest.raises(RuntimeError):
        handoff.import_bundle(bundle)

    # --force を付ければ上書きできる
    handoff.import_bundle(bundle, force=True)
    assert queue.list_posts() == []
