"""受信DMへの返信「下書き」を複数パターン生成する。

重要: このモジュールは下書きを作るだけで、送信は一切行わない。
実際の送信は必ず人間が内容を確認した上でXアプリから手動で行うこと。
自動DM送信はXの利用規約に違反するリスクがあるため、意図的にスコープ外にしている。
"""

from __future__ import annotations

import os
from typing import Any

from .. import config
from ..profile import store as profile_store

DEFAULT_MODEL = "claude-sonnet-5"


def _get_anthropic_client():
    try:
        import anthropic
    except ImportError:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def build_system_prompt(matching_criteria: str, grounding: str) -> str:
    return (
        "あなたはXのDM返信を代筆するアシスタントです。\n"
        "本人になりすますのではなく、本人の価値観に沿った返信案を複数提案します。\n"
        "誠実さを保ち、相手を欺いたり過度に持ち上げたりする文面は書かないでください。\n"
        "また、相手の同意や意思を尊重する書き方を優先してください。\n\n"
        f"[会いたい相手・大事にしたい価値観]\n{matching_criteria}\n\n"
        f"[本人プロフィール]\n{grounding}\n"
    )


def build_user_prompt(dm_text: str) -> str:
    return (
        "以下は相手から届いたDMです。これに対する返信案を3パターン、"
        "トーン違い(例: 落ち着いた/フレンドリー/簡潔)で提案してください。"
        "各案は1〜3文程度、番号付きで出力してください。\n\n"
        f"[受信したDM]\n{dm_text}"
    )


def draft_replies(dm_text: str, model: str | None = None, client=None) -> dict[str, Any]:
    """DM本文を渡し、返信案(複数)を生成する。送信は行わない。

    戻り値:
      - 生成できた場合: {"replies": str}  (Claudeの出力をそのまま返す。番号付きの複数案)
      - APIキー未設定の場合: {"fallback_prompt_path": str}
    """
    settings = config.load_settings()
    model = model or settings.get("model") or DEFAULT_MODEL
    matching_criteria = (settings.get("matching_criteria") or "").strip()
    grounding = profile_store.as_grounding_text()

    system_prompt = build_system_prompt(matching_criteria, grounding)
    user_prompt = build_user_prompt(dm_text)

    client = client if client is not None else _get_anthropic_client()
    if client is None:
        config.ensure_data_dirs()
        path = config.prompts_dir() / "dm_reply_prompt.txt"
        path.write_text(
            "# ANTHROPIC_API_KEY が未設定のため自動生成をスキップしました。\n"
            "# 下記を手動でClaude等に貼り付けて返信案を作成してください。\n\n"
            f"--- system ---\n{system_prompt}\n\n--- user ---\n{user_prompt}\n",
            encoding="utf-8",
        )
        return {"fallback_prompt_path": str(path)}

    resp = client.messages.create(
        model=model,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return {"replies": resp.content[0].text.strip()}
