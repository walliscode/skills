import pytest

from test_harness import harness


def test_regex_check_passes_when_pattern_matches_output():
    graded = harness.grade([{"type": "regex", "value": r"ZEPHYR-\d{4}"}], "the word is ZEPHYR-7741")
    assert graded == [{"type": "regex", "value": r"ZEPHYR-\d{4}", "passed": True}]


def test_regex_check_fails_when_pattern_does_not_match_output():
    graded = harness.grade([{"type": "regex", "value": r"ZEPHYR-\d{4}"}], "no word here")
    assert graded[0]["passed"] is False


def test_file_contains_check_passes_when_workspace_file_has_value(tmp_path):
    (tmp_path / "notes.txt").write_text("the canary is ZEPHYR-7741")
    check = {"type": "file_contains", "path": "notes.txt", "value": "ZEPHYR-7741"}

    graded = harness.grade([check], "", workspace=tmp_path)

    assert graded == [{**check, "passed": True}]


def test_file_contains_check_fails_when_value_missing_from_file(tmp_path):
    (tmp_path / "notes.txt").write_text("nothing relevant")
    check = {"type": "file_contains", "path": "notes.txt", "value": "ZEPHYR-7741"}

    assert harness.grade([check], "", workspace=tmp_path)[0]["passed"] is False


def test_file_contains_check_fails_when_file_is_absent(tmp_path):
    check = {"type": "file_contains", "path": "missing.txt", "value": "ZEPHYR-7741"}

    assert harness.grade([check], "", workspace=tmp_path)[0]["passed"] is False


def test_unknown_check_type_is_rejected():
    with pytest.raises(ValueError):
        harness.grade([{"type": "nope", "value": "x"}], "")
