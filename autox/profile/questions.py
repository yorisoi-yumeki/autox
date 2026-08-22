"""価値観インタビューの質問バンク。

目的: 投稿やDM下書きの「発信内容」が、実際に会ったときの本人の考え方と
乖離しないようにするため、運用開始前に本人の価値観・人柄を言語化しておく。
6カテゴリ x 6問 = 36問(30問以上)。

各質問は (category, key, question) のタプルで、key は
config/profile.yaml に保存する際のフィールド名になる。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    category: str       # カテゴリ表示名
    key: str             # profile.yaml に保存するキー
    text: str            # 質問文


QUESTION_BANK: list[Question] = [
    # --- 恋愛観・パートナーシップ観 ---
    Question("恋愛観・パートナーシップ観", "relationship_priority",
              "恋愛/パートナーシップにおいて、一番大事にしたいことは何ですか？"),
    Question("恋愛観・パートナーシップ観", "relationship_pace",
              "関係を深めるペースについて、理想はどのくらいですか？(すぐ会いたい/じっくり話してから 等)"),
    Question("恋愛観・パートナーシップ観", "relationship_honesty",
              "相手との関係で、正直でいたいと思うことは何ですか？隠したくないことはありますか？"),
    Question("恋愛観・パートナーシップ観", "relationship_dealbreaker",
              "恋愛/人間関係において、これだけは無理、というものはありますか？"),
    Question("恋愛観・パートナーシップ観", "relationship_ideal_time",
              "相手と過ごす理想の時間の使い方はどんなものですか？"),
    Question("恋愛観・パートナーシップ観", "relationship_past_lesson",
              "過去の恋愛/人間関係から学んだこと、今も大事にしていることはありますか？"),

    # --- コミュニケーションのスタイル ---
    Question("コミュニケーションのスタイル", "comm_style",
              "普段の会話やメッセージのやり取りで、自分らしいと感じる話し方・言葉遣いは？"),
    Question("コミュニケーションのスタイル", "comm_response_speed",
              "メッセージの返信速度について、自分の傾向とどうありたいかを教えてください。"),
    Question("コミュニケーションのスタイル", "comm_conflict",
              "意見が合わない時、どう対応するタイプですか？"),
    Question("コミュニケーションのスタイル", "comm_emoji",
              "絵文字や語尾、口癖など、文章に出やすい自分らしさはありますか？"),
    Question("コミュニケーションのスタイル", "comm_listening",
              "相手の話を聞くとき、大事にしていることはありますか？"),
    Question("コミュニケーションのスタイル", "comm_vulnerability",
              "弱みや悩みを人に話すのは得意ですか、苦手ですか？"),

    # --- 譲れない価値観・境界線 ---
    Question("譲れない価値観・境界線", "boundary_respect",
              "相手に対して絶対にしたくないこと(嘘をつく、雑に扱う 等)は何ですか？"),
    Question("譲れない価値観・境界線", "boundary_consent",
              "関係を進める上で、相手の意思確認について大事にしていることは？"),
    Question("譲れない価値観・境界線", "boundary_money",
              "お金の関わり方について、自分のスタンス(奢る/割り勘 等)はどうですか？"),
    Question("譲れない価値観・境界線", "boundary_privacy",
              "自分や相手のプライバシーについて、譲れないルールはありますか？"),
    Question("譲れない価値観・境界線", "boundary_no_go",
              "話題や行動として、絶対にNGだと思っていることは何ですか？"),
    Question("譲れない価値観・境界線", "boundary_safety",
              "安全に付き合う上で、自分なりに決めているルールはありますか？(会う場所、事前の確認等)"),

    # --- ライフスタイルの事実 ---
    Question("ライフスタイルの事実", "lifestyle_work",
              "仕事(業種・働き方の雰囲気程度でOK、特定できる情報は避けてください)について簡単に教えてください。"),
    Question("ライフスタイルの事実", "lifestyle_weekday",
              "平日の過ごし方はどんな感じですか？"),
    Question("ライフスタイルの事実", "lifestyle_weekend",
              "休日はどんな風に過ごすことが多いですか？"),
    Question("ライフスタイルの事実", "lifestyle_area",
              "普段活動しているエリア(都市部/地方 程度の粒度)はどこですか？"),
    Question("ライフスタイルの事実", "lifestyle_health",
              "体型・雰囲気について、自分から伝えておきたいことはありますか？"),
    Question("ライフスタイルの事実", "lifestyle_routine",
              "毎日/毎週欠かさずやっていることはありますか？"),

    # --- 人柄・ユーモア ---
    Question("人柄・ユーモア", "personality_humor",
              "自分のユーモアのタイプは？(天然/毒舌/ボケ役/ツッコミ役 等、自由に)"),
    Question("人柄・ユーモア", "personality_strength",
              "自分の長所だと思っているところは？"),
    Question("人柄・ユーモア", "personality_weakness",
              "自分の短所や、直したいと思っているところは？"),
    Question("人柄・ユーモア", "personality_hobby",
              "熱中している趣味や、最近ハマっていることは？"),
    Question("人柄・ユーモア", "personality_energy",
              "人といる時、自分はどちらかというと聞き役ですか、話し役ですか？"),
    Question("人柄・ユーモア", "personality_comfort",
              "どんな時に「自分らしくいられる」と感じますか？"),

    # --- 将来的に求める関係性 ---
    Question("将来的に求める関係性", "goal_relationship_type",
              "今、どんな関係性を求めていますか？(気軽な関係/真剣な交際/その他)"),
    Question("将来的に求める関係性", "goal_meeting_condition",
              "実際に会うとしたら、どんな条件が揃っていたら安心できますか？"),
    Question("将来的に求める関係性", "goal_red_flag",
              "相手にこういう様子が見えたら距離を置きたい、というサインはありますか？"),
    Question("将来的に求める関係性", "goal_green_flag",
              "相手にこういう様子が見えたら嬉しい、安心する、というサインはありますか？"),
    Question("将来的に求める関係性", "goal_timeline",
              "どのくらいの期間、この運用を続けてみたいと思っていますか？"),
    Question("将来的に求める関係性", "goal_success_definition",
              "自分にとって「うまくいった」と言える状態はどんな状態ですか？"),
]


def total_questions() -> int:
    return len(QUESTION_BANK)


def by_category() -> dict[str, list[Question]]:
    grouped: dict[str, list[Question]] = {}
    for q in QUESTION_BANK:
        grouped.setdefault(q.category, []).append(q)
    return grouped
