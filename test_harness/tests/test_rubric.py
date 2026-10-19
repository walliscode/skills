from test_harness import harness

SKILL = "harness-fixtures/canary-word"
CASE = {
    "prompt": "p",
    "checks": [{"type": "output_contains", "value": "ZEPHYR-7741"}],
    "rubric": "The reply names the canary word and nothing else.",
}


def text_event(text):
    return {"type": "text", "part": {"text": text}}


def test_rubric_does_not_run_when_a_check_fails():
    calls = []

    def judge(rubric, output):
        calls.append(rubric)
        return True

    record = harness.build_record(SKILL, "c", "m", CASE, [text_event("no word")], judge=judge)

    assert calls == []
    assert record["rubric"] is None
    assert record["passed"] is False


def test_rubric_runs_and_records_pass_when_checks_pass():
    record = harness.build_record(
        SKILL, "c", "m", CASE, [text_event("ZEPHYR-7741")], judge=lambda rubric, output: True
    )

    assert record["rubric"] == {"criteria": CASE["rubric"], "passed": True}
    assert record["passed"] is True


def test_rubric_failure_fails_the_run():
    record = harness.build_record(
        SKILL, "c", "m", CASE, [text_event("ZEPHYR-7741")], judge=lambda rubric, output: False
    )

    assert record["rubric"] == {"criteria": CASE["rubric"], "passed": False}
    assert record["passed"] is False


def test_rubric_is_skipped_when_case_has_none():
    case = {"prompt": "p", "checks": [{"type": "output_contains", "value": "ZEPHYR-7741"}]}
    calls = []

    record = harness.build_record(
        SKILL, "c", "m", case, [text_event("ZEPHYR-7741")], judge=lambda r, o: calls.append(r) or True
    )

    assert calls == []
    assert record["rubric"] is None
    assert record["passed"] is True


def test_grade_rubric_passes_only_on_a_bare_pass_reply(monkeypatch):
    replies = {"PASS": True, " pass \n": True, "FAIL": False, "maybe PASS": False}
    for reply, expected in replies.items():
        monkeypatch.setattr(harness, "run_opencode", lambda prompt, model, cwd=None: [text_event(reply)])
        assert harness.grade_rubric("criteria", "output", "m") is expected, reply
