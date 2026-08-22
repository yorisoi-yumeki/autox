"""profile.yaml (価値観インタビューの回答)の読み書きと対話インタビュー。"""

from __future__ import annotations

from typing import Callable

from .. import config
from .questions import QUESTION_BANK, Question, total_questions


def load() -> dict[str, str]:
    return config.load_profile()


def save(answers: dict[str, str]) -> None:
    config.save_profile(answers)


def unanswered_questions(answers: dict[str, str]) -> list[Question]:
    return [q for q in QUESTION_BANK if not answers.get(q.key, "").strip()]


def completion_rate(answers: dict[str, str]) -> float:
    total = total_questions()
    if total == 0:
        return 0.0
    answered = total - len(unanswered_questions(answers))
    return answered / total


def run_interview_cli(input_fn: Callable[[str], str] = input) -> dict[str, str]:
    """標準入力から1問ずつ質問し、回答を蓄積してprofile.yamlに保存する。

    既存の回答済み質問はスキップする(何度でも再実行して埋めていける)。
    空入力(Enterのみ)ならスキップ扱いで、その質問はunansweredのまま残る。
    """
    answers = load()
    to_ask = unanswered_questions(answers)
    if not to_ask:
        print("すべての質問に回答済みです。config/profile.yaml を直接編集して更新もできます。")
        return answers

    print(f"価値観インタビュー: 未回答 {len(to_ask)}問 / 全{total_questions()}問")
    print("(Enterだけ押すとスキップして次回に回せます)\n")

    current_category = None
    for q in to_ask:
        if q.category != current_category:
            current_category = q.category
            print(f"\n--- {current_category} ---")
        answer = input_fn(f"[{q.key}] {q.text}\n> ").strip()
        if answer:
            answers[q.key] = answer

    save(answers)
    rate = completion_rate(answers)
    print(f"\n保存しました: config/profile.yaml (回答率 {rate:.0%})")
    return answers


def as_grounding_text(answers: dict[str, str] | None = None) -> str:
    """content/generator.py や dm_assist から、生成AIへのシステムプロンプトに
    埋め込むための平文サマリを作る。未回答が多い場合はその旨も明記する。
    """
    answers = answers if answers is not None else load()
    if not answers:
        return "(本人プロフィール未登録。価値観インタビュー未実施のため、一般的なトーンで生成します。)"

    lines = ["以下はこのアカウントの本人が実際に答えた価値観・人柄です。これに矛盾しない内容にしてください。"]
    grouped: dict[str, list[str]] = {}
    for q in QUESTION_BANK:
        val = answers.get(q.key, "").strip()
        if val:
            grouped.setdefault(q.category, []).append(f"- {q.text} → {val}")
    for category, items in grouped.items():
        lines.append(f"\n[{category}]")
        lines.extend(items)

    rate = completion_rate(answers)
    if rate < 1.0:
        lines.append(f"\n(注: 価値観インタビューは {rate:.0%} しか回答されていません。未回答部分は一般的なトーンで補ってください。)")
    return "\n".join(lines)
