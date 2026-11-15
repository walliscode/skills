"""@file report.py
@brief Derived stats for the eval harness: group stored per-run records and format a report.

Nothing is stored here. Every stat is computed from the result JSON files when the report runs.
"""

# Standard library: reading result files and their names.
import json
from pathlib import Path


def summary_text(results_dir):
    """@brief Build the report text for every stored run.

    @param results_dir Folder of result JSON files.
    @return The formatted report.
    """
    return format_report(summarize(load_records(results_dir)))


def load_records(results_dir):
    """@brief Read every result file in a folder.

    @param results_dir Folder of result JSON files, e.g. `test_harness/results`.
    @return List of `(run_id, record)` pairs sorted by file name, where run_id is the file name without `.json`.
            Empty if the folder does not exist.
    """
    if not Path(results_dir).is_dir():
        return []
    return [(path.stem, json.loads(path.read_text())) for path in sorted(Path(results_dir).glob("*.json"))]


def run_passed(record):
    """@brief Say whether one stored run counts as a pass.

    A run passes only if the skill loaded and the stored pass flag (checks and rubric) is true.

    @param record A result dict from build_record().
    @return True if the run passed.
    """
    return bool(record["passed"] and record["skill_loaded"])


def label_suffix(label):
    """@brief Describe a group's label for a header line.

    @param label `working-tree` for a run of uncommitted edits, or None.
    @return A leading-space marker such as ` [working-tree]`, or an empty string.
    """
    return f" [{label}]" if label else ""


def group_key(record):
    """@brief Build the key that groups a stored run with its like.

    @param record A result dict from build_record().
    @return `(skill, case, model, arm, skill_hash, label)`, with an empty string for a committed run's label.
    """
    return (
        record["skill"],
        record["case"],
        record["model"],
        record["arm"],
        record["skill_hash"],
        record.get("label") or "",
    )


def summarize(runs):
    """@brief Group runs by skill, case, model, arm, skill hash and label, and derive the stats for each group.

    A change to a skill starts new groups, so its runs never mix with the old version's.
    Runs of uncommitted edits (label `working-tree`) never mix with committed runs.

    @param runs List of `(run_id, record)` pairs from load_records().
    @return List of group dicts, sorted by group key. Each has the key fields, `runs`, `passes`,
            `pass_rate`, `pass_variance`, `cost_per_run`, `cost_per_passing_run`, `failing_runs`,
            `checks_passed`, and `rubric` (`runs` and `passed` counts, or None if no run had a rubric).
            Costs are None when any run in the group has no recorded cost, or when no run passed.
    """
    groups = {}
    for run_id, record in runs:
        key = group_key(record)
        groups.setdefault(key, []).append((run_id, record))
    return [_summarize_group(key, members) for key, members in sorted(groups.items())]


def _summarize_group(key, members):
    """@brief Derive the stats for one group of runs.

    @param key `(skill, case, model, arm, skill_hash, label)` tuple.
    @param members List of `(run_id, record)` pairs in the group.
    @return The group dict described in summarize().
    """
    skill, case, model, arm, skill_hash, label = key
    label = label or None
    runs = len(members)
    passes = sum(1 for _, record in members if run_passed(record))
    pass_rate = passes / runs
    # Run-to-run variance of the pass/fail outcome, which is p * (1 - p) for 0/1 outcomes.
    pass_variance = pass_rate * (1 - pass_rate)

    costs = [record.get("cost") for _, record in members]
    # One unknown cost makes the total unknown, so a partial sum is never reported as a total.
    total = None if any(cost is None for cost in costs) else sum(costs)
    cost_per_run = None if total is None else total / runs
    cost_per_passing_run = None if total is None or passes == 0 else total / passes

    # Rubric verdicts are counted apart from the deterministic checks, so a failure can be attributed.
    rubric_verdicts = [record["rubric"]["passed"] for _, record in members if record.get("rubric")]
    rubric = {"runs": len(rubric_verdicts), "passed": sum(rubric_verdicts)} if rubric_verdicts else None
    checks_passed = sum(1 for _, record in members if all(check["passed"] for check in record["checks"]))

    return {
        "skill": skill,
        "case": case,
        "model": model,
        "arm": arm,
        "skill_hash": skill_hash,
        "label": label,
        "runs": runs,
        "passes": passes,
        "pass_rate": pass_rate,
        "pass_variance": pass_variance,
        "cost_per_run": cost_per_run,
        "cost_per_passing_run": cost_per_passing_run,
        "failing_runs": [run_id for run_id, record in members if not run_passed(record)],
        "checks_passed": checks_passed,
        "rubric": rubric,
    }


def _money(value):
    """@brief Format a cost for the report, or `null` when it is unknown.

    @param value A dollar amount, or None.
    @return The amount to four decimal places, or `null`.
    """
    return "null" if value is None else f"${value:.4f}"


def format_report(groups):
    """@brief Turn the group stats into the text the report command prints.

    @param groups List of group dicts from summarize().
    @return The report text, one block per group.
    """
    blocks = []
    for group in groups:
        lines = [
            f"{group['skill']} {group['case']} {group['model']} ({group['arm']})"
            f" hash {group['skill_hash'][:8]}{label_suffix(group['label'])}",
            f"  pass {group['passes']}/{group['runs']} ({group['pass_rate'] * 100:.1f}%)"
            f"  pass variance {group['pass_variance']:.3f}",
            f"  cost/run {_money(group['cost_per_run'])}"
            f"  cost/passing run {_money(group['cost_per_passing_run'])}",
            f"  checks passed {group['checks_passed']}/{group['runs']}",
        ]
        if group["rubric"] is not None:
            lines.append(f"  rubric passed {group['rubric']['passed']}/{group['rubric']['runs']}")
        if group["failing_runs"]:
            lines.append(f"  failing runs: {', '.join(group['failing_runs'])}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
