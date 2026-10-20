from test_harness import compare, report


def record(passed=True, skill_loaded=True, skill="s/canary", case="c", model="m", arm="with"):
    return {
        "skill": skill,
        "case": case,
        "model": model,
        "arm": arm,
        "skill_loaded": skill_loaded,
        "cost": 0.1,
        "checks": [{"type": "output_contains", "value": "x", "passed": passed}],
        "rubric": None,
        "passed": passed,
    }


def test_arm_comparison_pairs_with_and_without_for_the_same_skill_case_and_model():
    runs = [
        ("r1", record(passed=True, arm="with")),
        ("r2", record(passed=False, skill_loaded=False, arm="without")),
    ]

    comparisons = compare.arm_comparisons(report.summarize(runs))

    assert len(comparisons) == 1
    assert comparisons[0]["with"]["passes"] == 1
    assert comparisons[0]["without"]["passes"] == 0


def test_arm_comparison_leaves_a_missing_arm_as_none():
    comparisons = compare.arm_comparisons(report.summarize([("r1", record(arm="with"))]))

    assert comparisons[0]["without"] is None


def test_arm_comparison_reports_the_pass_rate_difference_in_points():
    runs = [
        ("r1", record(passed=True, arm="with")),
        ("r2", record(passed=True, arm="with")),
        ("r3", record(passed=False, skill_loaded=False, arm="without")),
        ("r4", record(passed=True, skill_loaded=False, arm="without")),
    ]

    text = compare.format_arm_comparison(compare.arm_comparisons(report.summarize(runs)))

    assert "with 2/2 (100.0%)" in text
    assert "without 0/2 (0.0%)" in text
    assert "delta +100.0 pts" in text


def test_arm_comparison_says_when_an_arm_has_no_runs():
    text = compare.format_arm_comparison(compare.arm_comparisons(report.summarize([("r1", record(arm="with"))])))

    assert "without: no runs" in text


def test_run_timelines_order_runs_by_their_file_name_stamp():
    runs = [
        ("20261019T100000Z__b", record(passed=False)),
        ("20261018T100000Z__a", record(passed=True)),
    ]

    timelines = compare.run_timelines(runs)

    assert timelines[("s/canary", "c", "m", "with")] == [
        ("20261018T100000Z__a", True),
        ("20261019T100000Z__b", False),
    ]


def test_run_timelines_skip_records_the_report_cannot_use():
    legacy = {"skill": "s/canary", "case": "c", "model": "m", "passed": True, "checks": []}

    assert compare.run_timelines([("old", legacy)]) == {}


def test_format_timelines_shows_each_run_in_order_and_the_pass_count():
    runs = [
        ("20261018T100000Z__a", record(passed=True)),
        ("20261019T100000Z__b", record(passed=False)),
        ("20261020T100000Z__c", record(passed=True)),
    ]

    text = compare.format_timelines(compare.run_timelines(runs))

    assert "s/canary c m (with)" in text
    assert "P F P  (2/3)" in text


def test_compare_command_prints_both_sections(tmp_path, monkeypatch, capsys):
    import json

    from test_harness import cli

    results = tmp_path / "test_harness" / "results"
    results.mkdir(parents=True)
    (results / "20261018T100000Z__a.json").write_text(json.dumps(record(passed=True, arm="with")))
    monkeypatch.chdir(tmp_path)

    code = cli.main(["compare"])

    assert code == 0
    out = capsys.readouterr().out
    assert "with 1/1 (100.0%)" in out
    assert "P  (1/1)" in out
