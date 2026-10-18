from test_harness import harness

CASE = {"prompt": "Use the canary-word skill.", "checks": []}


def skill_event(skill_id):
    return {
        "type": "tool_use",
        "part": {"tool": "skill", "state": {"input": {"id": skill_id}}},
    }


def record(events):
    return harness.build_record("harness-fixtures/canary-word", "reports-canary-word", "m", CASE, events)


def test_records_skill_loaded_when_skill_under_test_is_loaded():
    assert record([skill_event("canary-word")])["skill_loaded"] is True


def test_records_skill_not_loaded_when_no_skill_tool_use():
    assert record([{"type": "text", "part": {"text": "hi"}}])["skill_loaded"] is False


def test_records_skill_not_loaded_when_only_other_skill_loaded():
    assert record([skill_event("tdd")])["skill_loaded"] is False
