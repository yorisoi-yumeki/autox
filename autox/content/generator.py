"""投稿下書きの生成(Claude APIを使う。未接続でも動く)。

ANTHROPIC_API_KEY が設定されていれば anthropic 経由でその場で生成し、
posts テーブルに status=draft で保存する。
未設定の場合は生成をスキップし、プロンプトを data/prompts/ に書き出す。
その内容をClaude Code等に貼り付けて生成し、
`autox content add <category> "<本文>"` で取り込める。
"""

from __future__ import annotations

import datetime as dt
import os
import random
from pathlib import Path
from typing import Any

from .. import config
from ..profile import store as profile_store
from . import queue

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


def pick_pillar(settings: dict[str, Any], pillar_key: str | None = None) -> dict[str, Any]:
    pillars = settings.get("content_pillars") or []
    if not pillars:
        raise ValueError("config/settings.yaml に content_pillars が設定されていません。")
    if pillar_key:
        for p in pillars:
            if p.get("key") == pillar_key:
                return p
        available = ", ".join(p.get("key", "") for p in pillars)
        raise ValueError(f"content_pillars に '{pillar_key}' が見つかりません(候補: {available})")
    return random.choice(pillars)


def build_system_prompt(settings: dict[str, Any], grounding: str) -> str:
    tone = (settings.get("tone") or "").strip()
    voice_reference = (settings.get("voice_reference") or "").strip()
    voice_section = (
        f"\n[本人の実際の文体サンプル(他サービスのプロフィール文などから抜粋)]\n"
        f"{voice_reference}\n"
        "↑内容(固有名詞やエピソード)をそのままコピーせず、あくまで話し方・ユーモアの"
        "クセ・テンションを真似る参考としてのみ使ってください。\n"
        if voice_reference else ""
    )
    return (
        "あなたはX(旧Twitter)の投稿文を代筆するアシスタントです。\n"
        "本人になりすますのではなく、本人が実際に言いそうなことに忠実な下書きを作ります。\n"
        "誇張、他人の実績の流用(会えた実績の捏造等)、虚偽のエピソードは絶対に書かないでください。\n\n"
        f"[トーン]\n{tone}\n"
        f"{voice_section}\n"
        f"[本人プロフィール]\n{grounding}\n"
    )


def build_user_prompt(pillar: dict[str, Any]) -> str:
    label = pillar.get("label", pillar.get("key", ""))
    desc = pillar.get("description", "")
    return (
        f"カテゴリ「{label}」({desc})の投稿文を1件、日本語で書いてください。\n"
        "140字前後を目安に、Xの投稿としてそのまま使える1本の文章のみ出力してください。"
        "前置きの説明やハッシュタグの羅列は不要です。"
    )


def _write_prompt_fallback(system_prompt: str, user_prompt: str, pillar_key: str) -> Path:
    config.ensure_data_dirs()
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = config.prompts_dir() / f"post_{pillar_key}_{ts}.txt"
    path.write_text(
        "# ANTHROPIC_API_KEY が未設定のため自動生成をスキップしました。\n"
        "# 下記を手動でClaude等に貼り付けて生成し、\n"
        "# `autox content add <category> \"<本文>\"` で取り込んでください。\n\n"
        f"--- system ---\n{system_prompt}\n\n--- user ---\n{user_prompt}\n",
        encoding="utf-8",
    )
    return path


def check_consistency(text: str, grounding: str, model: str = DEFAULT_MODEL, client=None) -> str | None:
    """生成文が本人プロフィールと明確に矛盾しないか簡易チェックする。

    APIが使えない/呼び出しに失敗した場合はNoneを返し、生成自体は止めない
    (チェックはあくまで補助であり、必須のブロッカーにはしない)。
    """
    client = client if client is not None else _get_anthropic_client()
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            system=(
                "あなたは投稿文のファクトチェッカーです。以下の本人プロフィールと"
                "投稿下書きを比較し、明確な矛盾(本人にとって嘘になる記述)があれば"
                "1〜2文で指摘し、無ければ「矛盾なし」とだけ答えてください。"
            ),
            messages=[{
                "role": "user",
                "content": f"[本人プロフィール]\n{grounding}\n\n[投稿下書き]\n{text}",
            }],
        )
        result = resp.content[0].text.strip()
        if result and "矛盾なし" not in result:
            return result
        return None
    except Exception:
        return None


def generate_draft(pillar_key: str | None = None, model: str | None = None, client=None) -> dict[str, Any]:
    """投稿下書きを1件生成する。

    戻り値:
      - 生成できた場合: {"id", "category", "content", "warning"}
      - APIキー未設定でフォールバックした場合: {"fallback_prompt_path": str}
    """
    settings = config.load_settings()
    model = model or settings.get("model") or DEFAULT_MODEL
    grounding = profile_store.as_grounding_text()
    pillar = pick_pillar(settings, pillar_key)

    system_prompt = build_system_prompt(settings, grounding)
    user_prompt = build_user_prompt(pillar)

    client = client if client is not None else _get_anthropic_client()
    if client is None:
        path = _write_prompt_fallback(system_prompt, user_prompt, pillar["key"])
        return {"fallback_prompt_path": str(path)}

    resp = client.messages.create(
        model=model,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = resp.content[0].text.strip()
    warning = check_consistency(text, grounding, model=model, client=client)

    post_id = queue.add_draft(pillar["key"], text, warning=warning)
    return {"id": post_id, "category": pillar["key"], "content": text, "warning": warning}
