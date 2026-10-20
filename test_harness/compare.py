"""@file compare.py
@brief Compare the with and without arms, and show runs in order over time.

Reads the same stored records as the report command and groups them the same way.
"""

from test_harness import report

# Width, in characters, of a full bar in the over-time chart.
BAR_WIDTH = 20


def arm_comparisons(groups):
    """@brief Pair each skill, case and model's with group with its without group.

    @param groups Group dicts from report.summarize().
    @return List of dicts with `skill`, `case`, `model`, `with` and `without`, where a missing arm is None.
    """
    paired = {}
    for group in groups:
        key = (group["skill"], group["case"], group["model"], group["skill_hash"])
        paired.setdefault(
            key,
            {
                "skill": key[0],
                "case": key[1],
                "model": key[2],
                "skill_hash": key[3],
                "with": None,
                "without": None,
            },
        )
        paired[key][group["arm"]] = group
    return [paired[key] for key in sorted(paired)]


def _arm_text(name, group):
    """@brief Describe one arm's pass count, or say it has no runs.

    @param name `with` or `without`.
    @param group The group dict for that arm, or None.
    @return A short phrase for the comparison line.
    """
    if group is None:
        return f"{name}: no runs"
    return f"{name} {group['passes']}/{group['runs']} ({group['pass_rate'] * 100:.1f}%)"


def format_arm_comparison(comparisons):
    """@brief Turn the arm pairs into the text the compare command prints.

    The delta is with minus without, in percentage points. It is left out when either arm has no runs.

    @param comparisons List of pairs from arm_comparisons().
    @return The text, one line pair per skill, case and model.
    """
    blocks = []
    for item in comparisons:
        line = f"  {_arm_text('with', item['with'])}  {_arm_text('without', item['without'])}"
        if item["with"] is not None and item["without"] is not None:
            delta = (item["with"]["pass_rate"] - item["without"]["pass_rate"]) * 100
            line += f"  delta {delta:+.1f} pts"
        blocks.append(f"{item['skill']} {item['case']} {item['model']} hash {item['skill_hash'][:8]}\n{line}")
    return "\n\n".join(blocks)


def run_timelines(runs):
    """@brief Order each group's runs by time, as pass or fail.

    Runs are ordered by their file name, which starts with the UTC timestamp. Records the
    report cannot use are left out.

    @param runs List of `(run_id, record)` pairs from report.load_records().
    @return Dict of `(skill, case, model, arm, skill_hash)` to a list of `(run_id, passed)` in time order.
    """
    timelines = {}
    current, _ = report.split_current(runs)
    for run_id, record in sorted(current):
        key = (record["skill"], record["case"], record["model"], record["arm"], record["skill_hash"])
        timelines.setdefault(key, []).append((run_id, report.run_passed(record)))
    return timelines


def format_timelines(timelines):
    """@brief Turn the timelines into the bar chart the compare command prints.

    Each group gets a header, then one bar per run in time order. A bar's length is the
    running pass rate up to that run, so progress over time shows as the bars grow or shrink.

    @param timelines Dict from run_timelines().
    @return One block per group: a header line, then a line per run with its bar, outcome and running rate.
    """
    blocks = []
    for (skill, case, model, arm, skill_hash), runs in sorted(timelines.items()):
        lines = [f"{skill} {case} {model} ({arm}) hash {skill_hash[:8]}"]
        passes = 0
        for index, (_, passed) in enumerate(runs, start=1):
            passes += passed
            rate = passes / index
            bar = "█" * round(rate * BAR_WIDTH)
            outcome = "P" if passed else "F"
            lines.append(f"  {index:>3} {bar:<{BAR_WIDTH}} {outcome} {rate * 100:5.1f}%")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
