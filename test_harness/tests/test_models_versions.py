from test_harness import compare, report
import pytest


def record(passed=True, model="m1", case="c", arm="with", skill_hash="h1", cost: float | None = 0.1, timestamp="2026-01-01T00:00:00+00:00", n=3, skill="s/canary"):
    return {
        "skill": skill,
        "case": case,
        "model": model,
        "arm": arm,
        "skill_hash": skill_hash,
        "n": n,
        "skill_loaded": True,
        "cost": cost,
        "timestamp": timestamp,
        "checks": [{"type": "output_contains", "value": "x", "passed": passed}],
        "rubric": None,
        "passed": passed,
    }


def runs(*records):
    return [(f"run{i}", r) for i, r in enumerate(records)]


def test_model_table_totals_a_model_across_the_skills_cases():
    records = [
        record(model="m1", case="a", passed=True),
        record(model="m1", case="a", passed=True),
        record(model="m1", case="b", passed=True),
        record(model="m1", case="b", passed=False),
    ]

    [row] = report.model_table(report.summarize(runs(*records)))

    assert (row["skill"], row["model"], row["cases"], row["passes"], row["runs"]) == ("s/canary", "m1", 2, 3, 4)
    assert row["pass_rate"] == 0.75


def test_model_table_has_a_row_per_model_sorted_by_pass_rate():
    records = [
        record(model="weak", passed=False),
        record(model="strong", passed=True),
        record(model="strong", passed=True),
        record(model="weak", passed=True),
        record(model="weak", passed=False),
    ]

    rows = report.model_table(report.summarize(runs(*records)))

    assert [row["model"] for row in rows] == ["strong", "weak"]


def test_model_table_leaves_out_the_without_arm():
    records = [record(model="m1", arm="with", passed=True), record(model="m1", arm="without", passed=False)]

    [row] = report.model_table(report.summarize(runs(*records)))

    assert (row["passes"], row["runs"]) == (1, 1)


def test_model_table_gives_cost_per_passing_run_across_cases():
    records = [
        record(model="m1", case="a", passed=True, cost=0.2),
        record(model="m1", case="b", passed=False, cost=0.2),
    ]

    [row] = report.model_table(report.summarize(runs(*records)))

    assert row["cost_per_passing_run"] == 0.4


def test_model_table_has_no_cost_when_a_run_has_none():
    records = [record(model="m1", passed=True, cost=None)]

    [row] = report.model_table(report.summarize(runs(*records)))

    assert row["cost_per_passing_run"] is None


def test_model_table_text_names_each_skill_and_model_with_its_interval():
    records = [record(model="m1", passed=True), record(model="m1", passed=True), record(model="m1", passed=True)]

    text = report.format_model_table(report.model_table(report.summarize(runs(*records))))

    assert "s/canary" in text
    assert "m1" in text
    assert "95% interval 43.8%-100.0%" in text


def test_difference_interval_for_five_of_five_against_none_of_five():
    interval = report.difference_interval(5, 5, 0, 5)
    assert interval is not None
    low, high = interval

    assert low == pytest.approx(0.385, abs=0.01)
    assert high == pytest.approx(1.0)


def test_version_comparison_pairs_the_same_case_and_model_in_time_order():
    old = [record(skill_hash="old", timestamp="2026-01-01T00:00:00+00:00", passed=False)] * 5
    new = [record(skill_hash="new", timestamp="2026-02-01T00:00:00+00:00", passed=True)] * 5

    [item] = compare.version_comparisons(report.summarize(runs(*old, *new)))

    assert (item["from"]["skill_hash"], item["to"]["skill_hash"]) == ("old", "new")
    assert item["delta"] == 100.0
    assert item["inconclusive"] is False


def test_version_comparison_is_inconclusive_with_fewer_than_five_runs():
    old = [record(skill_hash="old", timestamp="2026-01-01T00:00:00+00:00", passed=True)] * 3
    new = [record(skill_hash="new", timestamp="2026-02-01T00:00:00+00:00", passed=True)] * 5

    [item] = compare.version_comparisons(report.summarize(runs(*old, *new)))

    assert item["inconclusive"] is True


def test_version_comparison_does_not_pair_legacy_with_new_runs():
    legacy = record(skill_hash="old", timestamp="2026-01-01T00:00:00+00:00")
    legacy.pop("n")
    new = record(skill_hash="new", timestamp="2026-02-01T00:00:00+00:00")

    assert compare.version_comparisons(report.summarize(runs(legacy, new))) == []


def test_version_comparison_text_shows_the_difference_and_interval():
    old = [record(skill_hash="old", timestamp="2026-01-01T00:00:00+00:00", passed=False)] * 5
    new = [record(skill_hash="new", timestamp="2026-02-01T00:00:00+00:00", passed=True)] * 5

    text = compare.format_version_comparison(compare.version_comparisons(report.summarize(runs(*old, *new))))

    assert "delta +100.0 pts" in text
