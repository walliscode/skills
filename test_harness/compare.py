"""@file compare.py
@brief Compare the with and without arms, and show runs in order over time.

Reads the same stored records as the report command and groups them the same way.
"""

from test_harness import report

# Width, in characters, of a full bar in the over-time chart.
BAR_WIDTH = 20


def arm_comparisons(groups):
    """@brief Pair each skill, case and model's with group with its without group.

    Legacy groups pair only with legacy groups, so old runs are never compared with new ones.
    A pair is inconclusive when either arm is missing or has fewer than `report.MIN_RUNS` runs.

    @param groups Group dicts from report.summarize().
    @return List of dicts with `skill`, `case`, `model`, `with`, `without`, `legacy` and `inconclusive`,
            where a missing arm is None.
    """
    paired = {}
    for group in groups:
        key = (
            group["skill"],
            group["case"],
            group["model"],
            group["skill_hash"],
            group["label"] or "",
            group["legacy"],
        )
        paired.setdefault(
            key,
            {
                "skill": key[0],
                "case": key[1],
                "model": key[2],
                "skill_hash": key[3],
                "label": key[4] or None,
                "legacy": key[5],
                "with": None,
                "without": None,
            },
        )
        paired[key][group["arm"]] = group
    comparisons = [paired[key] for key in sorted(paired)]
    for item in comparisons:
        arms = [item["with"], item["without"]]
        item["inconclusive"] = any(arm is None or arm["runs"] < report.MIN_RUNS for arm in arms)
    return comparisons


def _arm_text(name, group):
    """@brief Describe one arm's pass count and interval, or say it has no runs.

    @param name `with` or `without`.
    @param group The group dict for that arm, or None.
    @return A short phrase for the comparison line.
    """
    if group is None:
        return f"{name}: no runs"
    return (
        f"{name} {group['passes']}/{group['runs']} ({group['pass_rate'] * 100:.1f}%)"
        f" {report.interval_text(group['interval'])}"
    )


def format_arm_comparison(comparisons):
    """@brief Turn the arm pairs into the text the compare command prints.

    The delta is with minus without, in percentage points. It is left out when either arm has no runs.
    An inconclusive pair is marked, since its difference could be noise.

    @param comparisons List of pairs from arm_comparisons().
    @return The text, one line pair per skill, case and model.
    """
    blocks = []
    for item in comparisons:
        line = f"  {_arm_text('with', item['with'])}  {_arm_text('without', item['without'])}"
        if item["with"] is not None and item["without"] is not None:
            delta = (item["with"]["pass_rate"] - item["without"]["pass_rate"]) * 100
            line += f"  delta {delta:+.1f} pts"
        if item["inconclusive"]:
            line += f"  inconclusive: fewer than {report.MIN_RUNS} runs in an arm"
        header = f"{item['skill']} {item['case']} {item['model']} hash {item['skill_hash'][:8]}"
        blocks.append(f"{header}{report.label_suffix(item['label'])}{report.legacy_suffix(item['legacy'])}\n{line}")
    return "\n\n".join(blocks)


def run_timelines(runs):
    """@brief Order each group's runs by time, as pass or fail.

    Runs are ordered by their file name, which starts with the UTC timestamp.

    @param runs List of `(run_id, record)` pairs from report.load_records().
    @return Dict of `(skill, case, model, arm, skill_hash, label, legacy)` to a list of `(run_id, passed)` in time order.
    """
    timelines = {}
    for run_id, record in sorted(runs):
        key = report.group_key(record)
        timelines.setdefault(key, []).append((run_id, report.run_passed(record)))
    return timelines


def format_timelines(timelines):
    """@brief Turn the timelines into the bar chart the compare command prints.

    Each group gets a header with its pass count, then one bar per run in time order.
    A passing run is a full bar and a failing run is an empty bar, so the pass rate
    shows as the proportion of full bars over time.

    @param timelines Dict from run_timelines().
    @return One block per group: a header line (with the `working-tree` marker where it applies), then a line per run with its bar and outcome.
    """
    blocks = []
    for (skill, case, model, arm, skill_hash, label, legacy), runs in sorted(timelines.items()):
        passes = sum(1 for _, passed in runs if passed)
        header = f"{skill} {case} {model} ({arm}) hash {skill_hash[:8]}{report.label_suffix(label)}{report.legacy_suffix(legacy)}"
        lines = [f"{header} ({passes}/{len(runs)})"]
        for index, (_, passed) in enumerate(runs, start=1):
            bar = "█" * BAR_WIDTH if passed else ""
            outcome = "P" if passed else "F"
            lines.append(f"  {index:>3} {bar:<{BAR_WIDTH}} {outcome}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def comparison_text(results_dir):
    """@brief Build the with and without arm comparison, then each group's runs in time order.

    @param results_dir Folder of result JSON files.
    @return The formatted comparison and timelines.
    """
    runs = report.load_records(results_dir)
    comparisons = arm_comparisons(report.summarize(runs))
    return f"{format_arm_comparison(comparisons)}\n\n{format_timelines(run_timelines(runs))}"
