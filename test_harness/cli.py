"""@file cli.py
@brief Command-line entry point: `python -m test_harness [--skill <module>/<skill>] [--case <id>] -m <model>`.
"""

# Standard library: command-line parsing, printing errors.
import argparse
import sys
import time
from pathlib import Path

from test_harness import compare, harness, progress, report, run


def plan_runs(root, skill_arg, case_arg, model, config):
    """@brief Work out which (skill, case) pairs to run, and check each one is runnable.

    Checks everything before any run starts, so a bad skill, case or model fails
    without spending any model calls.

    @param root Repo root to look for skills under.
    @param skill_arg The `<module>/<skill>` given on the command line, or None for every skill.
    @param case_arg The case id given with `--case`, or None for every case in each skill.
    @param model The `provider/model` string requested with `-m`.
    @param config The loaded harness config.
    @return List of `(skill, case_dict)` pairs, in run order.
    @throws ValueError With a message for the user if something can't be run.
    """
    # With no skill argument, every skill that has an evals file is selected.
    skills = [skill_arg] if skill_arg else harness.discover_skills(root)
    if not skills:
        raise ValueError("no skills with evals/evals.yaml found")

    plan = []
    for skill in skills:
        skill_dir = root / skill
        # A skill without an evals file can't be run.
        if not harness.evals_path(skill_dir).is_file():
            raise ValueError(f"no {skill}/evals/evals.yaml")
        cases = harness.load_cases(skill_dir)
        if case_arg is not None:
            try:
                # Only the one requested case runs.
                cases = [harness.find_case(cases, case_arg)]
            except KeyError:
                # With no skill named, skip skills that don't have the case. With one named, that's an error.
                if skill_arg:
                    raise ValueError(f"no case '{case_arg}' in {skill}/evals/evals.yaml")
                continue
        for case in cases:
            # Refuse a model that the case (or the config list) doesn't allow.
            models = harness.allowed_models(case, config["models"])
            if model not in models:
                raise ValueError(f"model '{model}' must be one of: {', '.join(models)}")
            plan.append((skill, case))
    if not plan:
        raise ValueError(f"no skill has case '{case_arg}'")
    return plan


def find_root(start):
    """@brief Find the repo root: the nearest folder at or above `start` that holds `opencode.json`.

    @param start Folder to search up from.
    @return The repo root path, or None if no folder above `start` has `opencode.json`.
    """
    for folder in [start, *start.parents]:
        if (folder / "opencode.json").is_file():
            return folder
    return None


def report_command(results_dir):
    """@brief Print the derived stats for every stored run.

    @param results_dir Folder of result JSON files.
    @return The process exit code, always 0.
    """
    print(report.summary_text(results_dir))
    return 0


def compare_command(results_dir):
    """@brief Print the with and without arm comparison, then each group's runs in time order.

    @param results_dir Folder of result JSON files.
    @return The process exit code, always 0.
    """
    print(compare.comparison_text(results_dir))
    return 0


def progress_demo_command(argv):
    """@brief Play a fake batch through the progress display, so its look can be tried without model calls.

    @param argv Arguments after `progress-demo`: `--runs` and `--delay`.
    @return The process exit code, always 0.
    """
    parser = argparse.ArgumentParser(prog="test_harness progress-demo")
    parser.add_argument("--runs", type=int, default=12, help="how many fake runs to play")
    parser.add_argument("--delay", type=float, default=0.3, help="seconds to wait before each fake run")
    args = parser.parse_args(argv)

    bar = progress.Progress(args.runs)
    for index in range(args.runs):
        time.sleep(args.delay)
        # Every third run fails, so the pass count moves at a realistic pace.
        passed = index % 3 != 2
        label = "PASS" if passed else "FAIL"
        bar.completed(
            f"{label} demo/skill case-{index + 1} (demo/model, with)",
            skill="demo/skill",
            model="demo/model",
            passed=passed,
        )
    bar.close()
    return 0


def main(argv=None):
    """@brief Run eval cases for one or every skill, N times under each arm, and report each result.

    N comes from the harness config `runs`. Each run uses a fresh workspace built
    from the case's fixtures. The "with" arm runs first, then the "without" arm.

    With no `--skill` every skill in the repo runs. Without
    `--case` every case of each selected skill runs.

    `report` as the first argument prints derived stats from the stored results instead.
    `compare` as the first argument prints the with and without arms side by side, then runs over time.

    Exit codes: 0 if every "with" run passes, 1 if any "with" run fails, 2 for usage or opencode errors.
    A run that errors stops the loop, so earlier runs may already have written results.
    A session export that fails is recorded on its run, the loop carries on, and the exit code is 2 at the end.
    Results are written under `test_harness/results/` at the repo root, found from the current directory.

    @param argv Argument list, or None to use sys.argv.
    @return The process exit code.
    """
    args_list = sys.argv[1:] if argv is None else argv
    if args_list[:1] == ["progress-demo"]:
        return progress_demo_command(args_list[1:])
    # Work from the repo root, found from the current directory, so any folder inside the repo works.
    root = find_root(Path.cwd())
    if root is None:
        print("error: no opencode.json found in this folder or any folder above it", file=sys.stderr)
        return 2
    if args_list[:1] == ["report"]:
        return report_command(root / "test_harness" / "results")
    if args_list[:1] == ["compare"]:
        return compare_command(root / "test_harness" / "results")

    # Describe the command-line arguments: optional skill, case and model filters.
    parser = argparse.ArgumentParser(prog="test_harness")
    parser.add_argument(
        "--skill", help="<module>/<skill>, e.g. engineering/tdd; omit to run every skill"
    )
    parser.add_argument("--case", help="case id from the skill's evals/evals.yaml; omit to run every case")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="run skills with uncommitted edits; their records are labelled working-tree",
    )
    parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="provider/model passed to opencode -m; must be in the config list or the case's models",
    )
    # Read the arguments. This exits with an error message itself if one is missing.
    args = parser.parse_args(argv)

    config = harness.load_config()
    try:
        # Check every skill, case and model up front, before any run starts.
        plan = plan_runs(root, args.skill, args.case, args.model, config)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    try:
        # Refuse skills with uncommitted edits unless asked to run them, before any run starts.
        dirty = sorted({skill for skill, _ in plan if harness.skill_is_dirty(root, skill)})
    except harness.GitError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    if dirty and not args.allow_dirty:
        print(
            f"error: uncommitted changes in {', '.join(dirty)}; commit them or pass --allow-dirty",
            file=sys.stderr,
        )
        return 2

    return run.run_plan(root, plan, args.model, config, allow_dirty=args.allow_dirty)
