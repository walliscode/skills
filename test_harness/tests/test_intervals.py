import pytest

from test_harness import compare, report


def bounds(passes, runs):
    interval = report.wilson_interval(passes, runs)
    assert interval is not None
    return interval


def record(passed=True, skill_loaded=True, arm="with"):
    return {
        "skill": "s/canary",
        "case": "c",
        "model": "m",
        "arm": arm,
        "skill_hash": "h1",
        "n": 3,
        "skill_loaded": skill_loaded,
        "cost": 0.1,
        "checks": [{"type": "output_contains", "value": "x", "passed": passed}],
        "rubric": None,
        "passed": passed,
    }


def runs(*records):
    return [(f"run{i}", r) for i, r in enumerate(records)]


def test_wilson_interval_for_three_of_three_is_wide_and_stops_at_one():
    low, high = bounds(3, 3)

    assert low == pytest.approx(0.438, abs=0.001)
    assert high == pytest.approx(1.0)


def test_wilson_interval_for_zero_of_three_stops_at_zero():
    low, high = bounds(0, 3)

    assert low == pytest.approx(0.0)
    assert high == pytest.approx(0.562, abs=0.001)


def test_wilson_interval_narrows_as_runs_are_added():
    low_3, high_3 = bounds(3, 3)
    low_30, high_30 = bounds(30, 30)

    assert high_30 - low_30 < high_3 - low_3
    assert low_30 == pytest.approx(0.886, abs=0.001)


def test_wilson_interval_has_no_value_without_runs():
    assert report.wilson_interval(0, 0) is None


def test_report_shows_the_interval_for_each_group():
    text = report.format_report(report.summarize(runs(record(passed=True), record(passed=True), record(passed=True))))

    assert "95% interval 43.8%-100.0%" in text


def test_record_without_run_count_is_marked_legacy_and_kept_apart_from_new_runs():
    legacy = record(passed=True)
    legacy.pop("n")
    groups = report.summarize(runs(legacy, record(passed=True)))

    assert sorted(group["legacy"] for group in groups) == [False, True]
    assert "[legacy]" in report.format_report([group for group in groups if group["legacy"]])


def arms(with_passes, with_runs, without_passes, without_runs):
    records = []
    for index in range(with_runs):
        records.append(record(passed=index < with_passes, arm="with"))
    for index in range(without_runs):
        records.append(record(passed=index < without_passes, skill_loaded=index < without_passes, arm="without"))
    return compare.arm_comparisons(report.summarize(runs(*records)))


def test_comparison_is_inconclusive_when_either_arm_has_fewer_than_five_runs():
    [item] = arms(5, 5, 0, 4)

    assert item["inconclusive"] is True


def test_comparison_is_conclusive_when_both_arms_have_five_runs():
    [item] = arms(5, 5, 0, 5)

    assert item["inconclusive"] is False


def test_compare_text_shows_intervals_and_the_inconclusive_flag():
    text = compare.format_arm_comparison(arms(3, 3, 0, 5))

    assert "interval 43.8%-100.0%" in text
    assert "inconclusive" in text


def test_compare_text_does_not_flag_a_conclusive_comparison():
    text = compare.format_arm_comparison(arms(5, 5, 0, 5))

    assert "inconclusive" not in text
