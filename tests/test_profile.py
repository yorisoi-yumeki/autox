from autox.profile import questions, store


def test_question_bank_has_at_least_30_questions():
    assert questions.total_questions() >= 30


def test_completion_rate_and_grounding_text(isolated_env):
    assert store.load() == {}
    assert store.completion_rate({}) == 0.0

    answers = {"relationship_priority": "誠実さ"}
    text = store.as_grounding_text(answers)
    assert "誠実さ" in text
    assert "未登録" not in text  # 部分回答はあるので「未登録」文言は出ない

    store.save(answers)
    assert store.load()["relationship_priority"] == "誠実さ"


def test_grounding_text_when_empty():
    text = store.as_grounding_text({})
    assert "未登録" in text
