import json

import pytest

from test_harness import report


def record(passed=True, skill_loaded=True, cost: float | None = 0.1, checks=None, rubric=None, skill="s/canary", case="c", model="m", arm="with"):
    return {
        "skill": skill,
        "case": case,
        "model": model,
        "arm": arm,
        "skill_loaded": skill_loaded,
        "cost": cost,
        "checks": checks if checks is not None else [{"type": "output_contains", "value": "x", "passed": passed}],
        "rubric": rubric,
        "passed": passed,
    }


def runs(*records):
    return [(f"run{i}", r) for i, r in enumerate(records)]


def only_group(*records):
    groups = report.summarize(runs(*records))
    assert len(groups) == 1
    return groups[0]


def test_groups_runs_by_skill_case_model_and_arm():
    groups = report.summarize(
        runs(
            record(skill="s/a"),
            record(skill="s/a", arm="without"),
            record(skill="s/b"),
            record(skill="s/a", model="other"),
        )
    )

    keys = [(g["skill"], g["case"], g["model"], g["arm"]) for g in groups]
    assert keys == [
        ("s/a", "c", "m", "with"),
        ("s/a", "c", "m", "without"),
        ("s/a", "c", "other", "with"),
        ("s/b", "c", "m", "with"),
    ]


def test_counts_runs_and_passes_and_pass_rate():
    group = only_group(record(passed=True), record(passed=False), record(passed=True))

    assert group["runs"] == 3
    assert group["passes"] == 2
    assert group["pass_rate"] == pytest.approx(2 / 3)


def test_pass_variance_is_p_times_one_minus_p():
    group = only_group(record(passed=True), record(passed=False), record(passed=True))

    assert group["pass_variance"] == pytest.approx((2 / 3) * (1 / 3))


def test_cost_per_run_and_cost_per_passing_run():
    group = only_group(
        record(passed=True, cost=0.1),
        record(passed=False, cost=0.2),
        record(passed=True, cost=0.3),
    )

    assert group["cost_per_run"] == pytest.approx(0.2)
    assert group["cost_per_passing_run"] == pytest.approx(0.3)


def test_cost_per_passing_run_is_null_when_nothing_passed():
    group = only_group(record(passed=False, cost=0.1))

    assert group["cost_per_passing_run"] is None
    assert group["cost_per_run"] == pytest.approx(0.1)


def test_costs_are_null_when_any_run_has_no_cost():
    group = only_group(record(passed=True, cost=0.1), record(passed=True, cost=None))

    assert group["cost_per_run"] is None
    assert group["cost_per_passing_run"] is None


def test_failed_skill_load_counts_as_a_failure_even_if_checks_pass():
    group = only_group(record(passed=True, skill_loaded=False))

    assert group["passes"] == 0
    assert group["failing_runs"] == ["run0"]


def test_failing_run_ids_are_listed():
    group = only_group(record(passed=True), record(passed=False), record(passed=False))

    assert group["failing_runs"] == ["run1", "run2"]


def test_rubric_verdict_is_reported_apart_from_checks():
    group = only_group(
        record(passed=False, checks=[{"type": "output_contains", "value": "x", "passed": False}]),
        record(passed=False, checks=[{"type": "output_contains", "value": "x", "passed": True}], rubric={"criteria": "c", "passed": False}),
        record(passed=True, checks=[{"type": "output_contains", "value": "x", "passed": True}], rubric={"criteria": "c", "passed": True}),
    )

    assert group["checks_passed"] == 2
    assert group["rubric"] == {"runs": 2, "passed": 1}


def test_rubric_is_none_when_no_run_used_one():
    group = only_group(record(passed=True))

    assert group["rubric"] is None


def test_load_records_reads_each_result_file_with_its_run_id(tmp_path):
    (tmp_path / "run-a.json").write_text(json.dumps(record(passed=True)))
    (tmp_path / "run-b.json").write_text(json.dumps(record(passed=False)))

    loaded = report.load_records(tmp_path)

    assert [run_id for run_id, _ in loaded] == ["run-a", "run-b"]
    assert loaded[1][1]["passed"] is False


def test_load_records_is_empty_when_there_is_no_results_folder(tmp_path):
    assert report.load_records(tmp_path / "missing") == []


def test_records_without_arm_or_skill_loaded_are_left_out():
    legacy = {"skill": "s/canary", "case": "c", "model": "m", "passed": False, "checks": []}

    groups = report.summarize([("old", legacy), ("new", record(passed=True))])

    assert len(groups) == 1
    assert groups[0]["runs"] == 1


def test_format_report_shows_k_of_n_costs_and_failing_runs():
    groups = report.summarize(runs(record(passed=True, cost=0.1), record(passed=False, cost=0.2)))

    text = report.format_report(groups)

    assert "1/2" in text
    assert "cost/run $0.1500" in text
    assert "cost/passing run $0.3000" in text
    assert "failing runs: run1" in text


def test_format_report_says_null_when_cost_per_passing_run_is_unknown():
    text = report.format_report(report.summarize(runs(record(passed=False))))

    assert "cost/passing run null" in text


def test_report_command_prints_the_report_from_the_results_folder(tmp_path, monkeypatch, capsys):
    from test_harness import cli

    results = tmp_path / "test_harness" / "results"
    results.mkdir(parents=True)
    (results / "run-a.json").write_text(json.dumps(record(passed=True)))
    monkeypatch.chdir(tmp_path)

    code = cli.main(["report"])

    assert code == 0
    assert "1/1" in capsys.readouterr().out
