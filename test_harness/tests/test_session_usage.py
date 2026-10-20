import json
import subprocess

import pytest

from test_harness import harness

SKILL = "harness-fixtures/canary-word"
CASE = {"id": "reports-canary-word", "prompt": "p", "checks": []}
EXPORT = {
    "info": {
        "id": "ses_abc",
        "model": {"id": "claude-haiku-5.5", "providerID": "github-copilot"},
        "cost": 0.00030,
        "tokens": {"input": 6, "output": 221, "reasoning": 82, "cache": {"read": 14820, "write": 4572}},
    },
    "messages": [],
}


def text_event(text, session="ses_abc"):
    return {"type": "text", "sessionID": session, "part": {"text": text}}


def test_session_id_comes_from_the_first_event_that_has_one():
    events = [{"type": "step_start"}, text_event("hi", session="ses_xyz")]

    assert harness.session_id(events) == "ses_xyz"


def test_session_id_is_none_when_no_event_has_one():
    assert harness.session_id([{"type": "text", "part": {"text": "hi"}}]) is None


def test_session_usage_reads_cost_and_tokens_from_export():
    usage = harness.session_usage(EXPORT)

    assert usage == {"cost": 0.00030, "tokens": {"input": 6, "output": 221, "cached": 14820}}


def test_session_usage_records_nulls_when_export_is_missing():
    assert harness.session_usage(None) == {
        "cost": None,
        "tokens": {"input": None, "output": None, "cached": None},
    }


def test_session_usage_records_nulls_for_fields_the_export_lacks():
    usage = harness.session_usage({"info": {"cost": 0.1}})

    assert usage == {"cost": 0.1, "tokens": {"input": None, "output": None, "cached": None}}


MULTI_STEP_EXPORT = {
    "info": {
        "id": "ses_multi",
        "model": {"id": "claude-haiku-5.5", "providerID": "github-copilot", "variant": "default"},
        "cost": 0.0002665,
        "tokens": {"input": 6, "output": 175, "reasoning": 60, "cache": {"read": 14840, "write": 4568}},
    },
    "messages": [
        {"type": "user", "text": "tell me the canary word"},
        {
            "type": "assistant",
            "model": {"id": "claude-haiku-5.5", "providerID": "github-copilot", "variant": "default"},
            "cost": 0.00010755,
            "tokens": {"input": 4, "output": 50, "reasoning": 60, "cache": {"read": 5215, "write": 4410}},
        },
        {
            "type": "assistant",
            "model": {"id": "claude-haiku-5.5", "providerID": "github-copilot", "variant": "default"},
            "cost": 0.00015895,
            "tokens": {"input": 2, "output": 125, "reasoning": 0, "cache": {"read": 9625, "write": 158}},
        },
        {"type": "outcome"},
    ],
}


def test_session_usage_of_multi_step_export_reads_session_totals():
    usage = harness.session_usage(MULTI_STEP_EXPORT)

    assert usage == {"cost": 0.0002665, "tokens": {"input": 6, "output": 175, "cached": 14840}}


def test_multi_step_session_totals_equal_the_sum_of_their_messages():
    steps = [message for message in MULTI_STEP_EXPORT["messages"] if message["type"] == "assistant"]

    assert sum(step["tokens"]["input"] for step in steps) == MULTI_STEP_EXPORT["info"]["tokens"]["input"]
    assert sum(step["tokens"]["output"] for step in steps) == MULTI_STEP_EXPORT["info"]["tokens"]["output"]
    assert sum(step["tokens"]["cache"]["read"] for step in steps) == MULTI_STEP_EXPORT["info"]["tokens"]["cache"]["read"]
    assert sum(step["cost"] for step in steps) == pytest.approx(MULTI_STEP_EXPORT["info"]["cost"])


def test_session_usage_records_nulls_for_tokens_without_cache():
    usage = harness.session_usage({"info": {"cost": 0.1, "tokens": {"input": 3, "output": 4}}})

    assert usage == {"cost": 0.1, "tokens": {"input": 3, "output": 4, "cached": None}}


def test_export_session_raises_with_stderr_when_opencode_fails(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom\n")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)

    with pytest.raises(harness.ExportError, match="boom"):
        harness.export_session("ses_abc")


def test_export_session_raises_when_output_is_not_json(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="not json", stderr="")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)

    with pytest.raises(harness.ExportError, match="not valid JSON"):
        harness.export_session("ses_abc")


def test_export_session_returns_none_without_a_session_id():
    assert harness.export_session(None) is None


def test_export_session_raises_when_opencode_is_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("opencode")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)

    with pytest.raises(harness.ExportError, match="opencode"):
        harness.export_session("ses_abc")


def test_export_session_parses_the_export_json(monkeypatch):
    def fake_run(args, **kwargs):
        assert args == ["opencode", "session", "export", "ses_abc"]
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(EXPORT), stderr="")

    monkeypatch.setattr(harness.subprocess, "run", fake_run)

    assert harness.export_session("ses_abc") == EXPORT


def test_build_record_includes_session_id_timestamp_cost_and_tokens():
    record = harness.build_record(SKILL, "c", "m", CASE, [text_event("hi")], session=EXPORT)

    assert record["session_id"] == "ses_abc"
    assert record["cost"] == 0.00030
    assert record["tokens"] == {"input": 6, "output": 221, "cached": 14820}
    assert record["timestamp"].endswith("+00:00")


def test_build_record_uses_null_usage_when_there_is_no_export():
    record = harness.build_record(SKILL, "c", "m", CASE, [text_event("hi")])

    assert record["cost"] is None
    assert record["tokens"] == {"input": None, "output": None, "cached": None}
