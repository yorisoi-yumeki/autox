"""autox CLI エントリポイント。

`python -m autox <subcommand>` または(pip install -e . 後は)`autox <subcommand>` で使う。
自動化しているのは下書き生成・予約カレンダー作成・分析・DM下書きまで。
実際の投稿・DM送信・フォロー操作は行わない(必ず人間が手動で行う)。
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from .analytics import report as analytics_report
from .analytics import tracker as analytics_tracker
from .content import generator, queue
from .dm_assist import draft_reply
from . import handoff
from .profile import store as profile_store
from .scheduling import scheduler


def _cmd_profile_interview(args: argparse.Namespace) -> None:
    profile_store.run_interview_cli()


def _cmd_profile_status(args: argparse.Namespace) -> None:
    answers = profile_store.load()
    rate = profile_store.completion_rate(answers)
    remaining = profile_store.unanswered_questions(answers)
    print(f"回答率: {rate:.0%}")
    if remaining:
        print(f"未回答: {len(remaining)}問 (`autox profile interview` で続きから回答できます)")
        for q in remaining:
            print(f"  - [{q.key}] {q.text}")
    else:
        print("すべて回答済みです。")


def _cmd_content_generate(args: argparse.Namespace) -> None:
    result = generator.generate_draft(pillar_key=args.pillar)
    if "fallback_prompt_path" in result:
        print("ANTHROPIC_API_KEY が未設定のため、プロンプトをファイルに書き出しました:")
        print(f"  {result['fallback_prompt_path']}")
        print("内容をClaude等に貼り付けて生成し、`autox content add <category> \"<本文>\"` で取り込んでください。")
        return
    print(f"下書き #{result['id']} ({result['category']}) を作成しました:")
    print(f"  {result['content']}")
    if result.get("warning"):
        print(f"  ⚠ 整合性チェックで指摘あり: {result['warning']}")


def _cmd_content_add(args: argparse.Namespace) -> None:
    post_id = queue.add_draft(args.category, args.content)
    print(f"下書き #{post_id} ({args.category}) を追加しました。")


def _cmd_content_list(args: argparse.Namespace) -> None:
    posts = queue.list_posts(status=args.status)
    if not posts:
        print("該当する投稿はありません。")
        return
    for p in posts:
        warn = f" ⚠{p.warning}" if p.warning else ""
        print(f"[{p.id}] ({p.status}/{p.category}) {p.content}{warn}")


def _cmd_content_approve(args: argparse.Namespace) -> None:
    queue.approve(args.id)
    print(f"下書き #{args.id} を承認しました。")


def _cmd_content_reject(args: argparse.Namespace) -> None:
    queue.reject(args.id)
    print(f"下書き #{args.id} を却下しました。")


def _cmd_schedule_run(args: argparse.Namespace) -> None:
    seed = args.seed
    assignments = scheduler.schedule_pending(seed=seed)
    if not assignments:
        print("承認済み(approved)の下書きがありません。`autox content approve <id>` で承認してください。")
        return
    path = scheduler.export_calendar_csv(assignments)
    print(f"{len(assignments)}件を投稿カレンダーに割り当てました: {path}")
    for post, when in assignments:
        print(f"  {when.strftime('%Y-%m-%d %H:%M')}  [{post.category}] {post.content}")
    print("\n※ 自動投稿は行いません。カレンダーの時刻に手動で投稿してください。")


def _cmd_analytics_log(args: argparse.Namespace) -> None:
    date = dt.date.fromisoformat(args.date) if args.date else None
    analytics_tracker.log_snapshot(
        followers=args.followers,
        likes=args.likes,
        replies=args.replies,
        impressions=args.impressions,
        date=date,
    )
    print("記録しました。")


def _cmd_analytics_report(args: argparse.Namespace) -> None:
    path = analytics_report.generate_report()
    print(f"レポートを生成しました: {path}")


def _cmd_dm_draft(args: argparse.Namespace) -> None:
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            dm_text = f.read()
    else:
        print("DM本文を貼り付けてください(入力後 Ctrl-D / Ctrl-Z で確定):")
        dm_text = sys.stdin.read()

    result = draft_reply.draft_replies(dm_text)
    if "fallback_prompt_path" in result:
        print("ANTHROPIC_API_KEY が未設定のため、プロンプトをファイルに書き出しました:")
        print(f"  {result['fallback_prompt_path']}")
        return
    print(result["replies"])
    print("\n※ 送信は行いません。内容を確認のうえ、ご自身でXアプリから送信してください。")


def _cmd_handoff_export(args: argparse.Namespace) -> None:
    path = handoff.write_bundle(Path(args.out) if args.out else None)
    print(f"引き継ぎバンドルを書き出しました: {path}")
    print("このファイルの中身を次のセッション(別環境・別デバイス含む)に渡し、")
    print(f"`autox handoff import {path}` で復元してください。")


def _cmd_handoff_import(args: argparse.Namespace) -> None:
    data = handoff.read_bundle(Path(args.path))
    try:
        counts = handoff.import_bundle(data, force=args.force)
    except RuntimeError as e:
        print(f"エラー: {e}")
        sys.exit(1)
    print(f"復元しました: 下書き{counts['posts']}件 / スナップショット{counts['snapshots']}件")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autox", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("profile", help="価値観インタビュー(本人プロフィール)")
    profile_sub = p_profile.add_subparsers(dest="profile_command", required=True)
    profile_sub.add_parser("interview", help="未回答の質問に順番に回答する").set_defaults(func=_cmd_profile_interview)
    profile_sub.add_parser("status", help="回答状況を表示する").set_defaults(func=_cmd_profile_status)

    p_content = sub.add_parser("content", help="投稿下書きの生成・管理")
    content_sub = p_content.add_subparsers(dest="content_command", required=True)

    p_gen = content_sub.add_parser("generate", help="下書きを1件AI生成する")
    p_gen.add_argument("--pillar", help="content_pillarsのkeyを指定(省略時はランダム)")
    p_gen.set_defaults(func=_cmd_content_generate)

    p_add = content_sub.add_parser("add", help="手動で書いた下書きを登録する")
    p_add.add_argument("category")
    p_add.add_argument("content")
    p_add.set_defaults(func=_cmd_content_add)

    p_list = content_sub.add_parser("list", help="下書き一覧を表示する")
    p_list.add_argument("--status", choices=["draft", "approved", "rejected", "scheduled", "posted"])
    p_list.set_defaults(func=_cmd_content_list)

    p_approve = content_sub.add_parser("approve", help="下書きを承認する")
    p_approve.add_argument("id", type=int)
    p_approve.set_defaults(func=_cmd_content_approve)

    p_reject = content_sub.add_parser("reject", help="下書きを却下する")
    p_reject.add_argument("id", type=int)
    p_reject.set_defaults(func=_cmd_content_reject)

    p_schedule = sub.add_parser("schedule", help="承認済み下書きを投稿カレンダーに割り当てる")
    schedule_sub = p_schedule.add_subparsers(dest="schedule_command", required=True)
    p_run = schedule_sub.add_parser("run", help="ゴールデンタイム帯のランダム時刻に割り当てる")
    p_run.add_argument("--seed", type=int, help="乱数シード(テスト・再現用)")
    p_run.set_defaults(func=_cmd_schedule_run)

    p_analytics = sub.add_parser("analytics", help="日次スナップショットの記録・レポート")
    analytics_sub = p_analytics.add_subparsers(dest="analytics_command", required=True)

    p_log = analytics_sub.add_parser("log", help="日次スナップショットを記録する")
    p_log.add_argument("--followers", type=int, required=True)
    p_log.add_argument("--likes", type=int, required=True)
    p_log.add_argument("--replies", type=int, required=True)
    p_log.add_argument("--impressions", type=int, required=True)
    p_log.add_argument("--date", help="YYYY-MM-DD(省略時は今日)")
    p_log.set_defaults(func=_cmd_analytics_log)

    p_report = analytics_sub.add_parser("report", help="HTMLレポートを生成する")
    p_report.set_defaults(func=_cmd_analytics_report)

    p_dm = sub.add_parser("dm", help="DM返信の下書き支援(送信はしない)")
    dm_sub = p_dm.add_subparsers(dest="dm_command", required=True)
    p_dm_draft = dm_sub.add_parser("draft", help="受信DMへの返信案を生成する")
    p_dm_draft.add_argument("--input", help="DM本文が書かれたファイルパス(省略時は標準入力)")
    p_dm_draft.set_defaults(func=_cmd_dm_draft)

    p_handoff = sub.add_parser(
        "handoff",
        help="profile/settings/下書きキューをまとめてexport/importする(セッション・環境間の引き継ぎ用)",
    )
    handoff_sub = p_handoff.add_subparsers(dest="handoff_command", required=True)

    p_h_export = handoff_sub.add_parser("export", help="現在の状態を1ファイルにまとめて書き出す")
    p_h_export.add_argument("--out", help="出力先パス(省略時 data/handoff_bundle.yaml)")
    p_h_export.set_defaults(func=_cmd_handoff_export)

    p_h_import = handoff_sub.add_parser("import", help="バンドルファイルから状態を復元する")
    p_h_import.add_argument("path")
    p_h_import.add_argument("--force", action="store_true", help="既存データがあっても上書きする")
    p_h_import.set_defaults(func=_cmd_handoff_import)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
