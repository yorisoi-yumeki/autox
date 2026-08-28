# autox

X(旧Twitter)アカウントの「投稿下書き生成・予約カレンダー作成」「分析・レポート」
「DM返信の下書き支援」「アカウント設計」を支援するCLIツール。

**このツールが自動化しないこと**: 投稿の自動送信、DMの自動送信、自動フォロー/
アンフォロー、自動いいね等の水増し行為。理由は `docs/compliance_notes.md` を参照。
X APIがまだ未接続の間は、下書き作成までを支援し、実際の投稿・DM送信は人間が
手動で行う設計になっている。

## できること

| コマンド | 内容 |
|---|---|
| `autox profile interview` | 30問以上の価値観インタビューに回答し、`config/profile.yaml` を作る |
| `autox content generate` | 投稿下書きをAIで1件生成(本人プロフィールを踏まえる) |
| `autox content list / approve / reject` | 下書きキューの管理 |
| `autox schedule run` | 承認済み下書きをゴールデンタイム帯のランダム時刻で投稿カレンダーに割当 |
| `autox analytics log` | フォロワー数等の日次スナップショットを記録 |
| `autox analytics report` | 成長率・エンゲージメント率のHTMLレポートを生成 |
| `autox dm draft` | 受信DMへの返信案を複数生成(送信はしない) |

## セットアップ

```bash
pip install -e ".[ai,dev]"   # anthropic(生成AI用)とpytestを含める場合
cp config/settings.example.yaml config/settings.yaml
cp .env.example .env          # ANTHROPIC_API_KEY を設定する場合のみ編集
```

`ANTHROPIC_API_KEY` が未設定でも動作する。その場合、生成系のコマンドは
`data/prompts/` にプロンプトを書き出すので、それをClaude等に貼り付けて
生成した本文を `autox content add <category> "<本文>"` で取り込める。

## 最初にやること: 価値観インタビュー

```bash
autox profile interview
```

投稿やDM下書きが「発信している人格」と「実際に会ったときの本人」で
乖離しないようにするための質問に答える。必須(中核)の質問が34問、
時間があれば答える任意の質問が1問あり、任意の質問は答えなくても
プロフィールとして完成扱いになる。質問は抽象的な自己評定ではなく、
直近の具体的なエピソードを聞く形にしてあるので、答えやすいはず。
途中で止めても続きから再開できる(`autox profile status` で回答状況を確認できる)。

## 基本的な流れ

```bash
autox content generate                 # 下書きを1件生成
autox content list --status draft      # 内容を確認
autox content approve 1                # 良ければ承認
autox schedule run                     # ゴールデンタイム帯のランダム時刻に割当
                                        # → data/post_calendar.csv を見て手動投稿

autox analytics log --followers 120 --likes 30 --replies 5 --impressions 4000
autox analytics report                 # data/reports/report_*.html を生成
```

## セッション・環境をまたいだ引き継ぎ(handoff)

`config/profile.yaml`・`config/settings.yaml`・`data/autox.db`(下書きキュー・
分析スナップショット)は個人情報のため `.gitignore` 対象で、Git経由では運ばれない。
特にクラウド/リモート実行環境では、セッションを新規に開始するたびにリポジトリが
まっさらに再クローンされるだけなので、前回セッションのこれらのファイルは
自動的には引き継がれない。

```bash
autox handoff export              # data/handoff_bundle.yaml に現在の状態をまとめる
autox handoff import <path>       # そのファイルから復元する(--force で既存データを上書き)
```

会話コンテキストが肥大化してリセットしたい時や、別のデバイス・実行環境で続きを
やりたい時は、`handoff export` の出力をコピーして次のセッションに渡し、
`handoff import` で復元してから作業を再開する。「経緯の要約」ではなく
実データそのものを運ぶことで、引き継ぎ時の抜け漏れを防ぐ。

## X APIを取得したら

`autox/scheduling/poster_stub.py` に実装手順をまとめてある。現状は
`NotImplementedError` を返すだけのスタブで、自動投稿・自動DM送信の実装は
含まれていない。

## ドキュメント

- `docs/account_strategy.md`: プロフィール文・固定ポストの設計ガイド(正直な自己開示ベース)
- `docs/compliance_notes.md`: このツールが自動化しない行為とその理由
