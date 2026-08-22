"""将来、X APIで自動投稿する場合の差し込み口(現時点では未実装)。

現在はX APIアクセスがないため、scheduler.py が作った投稿カレンダーを見て
ユーザーが手動で投稿する運用を前提にしている。

X API Basic tier以上を取得したら、以下の方針で実装する想定:
  1. `pip install tweepy` を追加依存に加える
  2. TweepyPoster クラスで tweepy.Client を初期化(API keyはconfig/settings.yamlや
     環境変数から読む。リポジトリには絶対にコミットしない)
  3. scheduling/scheduler.py 側から、scheduled_at が到来した投稿を
     `poster.post(content, scheduled_at)` で送信し、成功したら
     `content.queue.mark_posted(post_id)` を呼ぶ
  4. cron/GitHub Actions等の定期実行で「今の時刻に投稿予定のものを処理する」
     ループを回す(常駐プロセスにする必要はない)

このスタブの目的は、実装時にここだけ差し替えれば済むよう境界を決めておくこと。
自動フォロー/アンフォロー、自動いいね、自動DM送信はここでは扱わない
(docs/compliance_notes.md を参照)。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol


@dataclass
class PostResult:
    success: bool
    remote_id: str | None = None
    error: str | None = None


class Poster(Protocol):
    def post(self, content: str, scheduled_at: dt.datetime) -> PostResult:
        ...


class NotConfiguredPoster:
    """X APIが未接続であることを明示するためのデフォルト実装。"""

    def post(self, content: str, scheduled_at: dt.datetime) -> PostResult:
        raise NotImplementedError(
            "X APIがまだ接続されていません。手動で投稿カレンダーの内容を投稿するか、"
            "X API Basic tier以上を取得後、このファイルのdocstringに沿って実装してください。"
        )
