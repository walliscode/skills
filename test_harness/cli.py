"""@file cli.py
@brief Command-line entry point: `python -m test_harness [<module>/<skill>] [--case <id>] -m <model>`.
"""

# Standard library: command-line parsing, deleting folders, printing errors and paths.
import argparse
import shutil
import sys
from pathlib import Path

from test_harness import compare, harness, report

# The two arms every case runs under, in order: skill available, then skill denied.
ARMS = ("with", "without")


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


def report_command(results_dir):
    """@brief Print the derived stats for every stored run.

    @param results_dir Folder of result JSON files.
    @return The process exit code, always 0.
    """
    runs, skipped = report.split_current(report.load_records(results_dir))
    if skipped:
        print(f"note: skipped {skipped} older result(s) without arm, skill_loaded, skill_hash or n", file=sys.stderr)
    print(report.format_report(report.summarize(runs)))
    return 0


def compare_command(results_dir):
    """@brief Print the with and without arm comparison, then each group's runs in time order.

    @param results_dir Folder of result JSON files.
    @return The process exit code, always 0.
    """
    runs = report.load_records(results_dir)
    _, skipped = report.split_current(runs)
    if skipped:
        print(f"note: skipped {skipped} older result(s) without arm, skill_loaded, skill_hash or n", file=sys.stderr)
    comparisons = compare.arm_comparisons(report.summarize(runs))
    print(compare.format_arm_comparison(comparisons))
    print()
    print(compare.format_timelines(compare.run_timelines(runs)))
    return 0


def main(argv=None):
    """@brief Run eval cases for one or every skill, N times under each arm, and report each result.

    N comes from the harness config `runs`. Each run uses a fresh workspace built
    from the case's fixtures. The "with" arm runs first, then the "without" arm.

    With no skill argument every skill under the current directory runs. Without
    `--case` every case of each selected skill runs.

    `report` as the first argument prints derived stats from the stored results instead.
    `compare` as the first argument prints the with and without arms side by side, then runs over time.

    Exit codes: 0 if every "with" run passes, 1 if any "with" run fails, 2 for usage or opencode errors.
    A run that errors stops the loop, so earlier runs may already have written results.
    Results are written under `test_harness/results/` in the current directory.

    @param argv Argument list, or None to use sys.argv.
    @return The process exit code.
    """
    args_list = sys.argv[1:] if argv is None else argv
    if args_list[:1] == ["report"]:
        return report_command(Path.cwd() / "test_harness" / "results")
    if args_list[:1] == ["compare"]:
        return compare_command(Path.cwd() / "test_harness" / "results")

    # Describe the command-line arguments: an optional skill path, an optional case id, and the model.
    parser = argparse.ArgumentParser(prog="test_harness")
    parser.add_argument(
        "skill", nargs="?", help="<module>/<skill>, e.g. engineering/tdd; omit to run every skill"
    )
    parser.add_argument("--case", help="case id from the skill's evals/evals.yaml; omit to run every case")
    parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="provider/model passed to opencode -m; must be in the config list or the case's models",
    )
    # Read the arguments. This exits with an error message itself if one is missing.
    args = parser.parse_args(argv)

    # Work from the current directory, which is where the skill folders live.
    root = Path.cwd()
    config = harness.load_config()
    try:
        # Check every skill, case and model up front, before any run starts.
        plan = plan_runs(root, args.skill, args.case, args.model, config)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    # Sent verbatim. Both arms run for every case: "with" leaves the skill
    # available, "without" denies it. Only the "with" arm decides the exit code,
    # since "without" is the baseline and is expected to fail the checks.
    # Starts as passing and is turned off by any failing "with" run.
    all_passed = True
    for skill, case in plan:
        skill_hash = harness.skill_hash(root / skill)
        for arm in ARMS:
            # Repeat each arm N times, from the config's `runs` value.
            for _ in range(config["runs"]):
                # A new workspace for each run, so no run sees another's files.
                workspace = harness.make_workspace(root, skill, case["id"], arm=arm)
                try:
                    # Run the prompt in the workspace, then grade the result there.
                    events = harness.run_opencode(case["prompt"], args.model, cwd=workspace)
                    # Export the session for its cost and token counts. A missing export is recorded as null.
                    session = harness.export_session(harness.session_id(events), cwd=workspace)
                    record = harness.build_record(
                        skill,
                        case["id"],
                        args.model,
                        case,
                        events,
                        arm=arm,
                        workspace=workspace,
                        judge=lambda criteria, output: harness.grade_rubric(criteria, output, args.model),
                        session=session,
                        skill_hash=skill_hash,
                        n=config["runs"],
                    )
                except harness.OpencodeError as err:
                    # opencode itself failed, so this is an error (exit 2), not a graded FAIL.
                    print(f"error: {err}", file=sys.stderr)
                    return 2
                finally:
                    # Always delete the workspace, even on error. Grading has already read the files.
                    shutil.rmtree(workspace, ignore_errors=True)

                # Save the graded record to test_harness/results/ and get its path.
                path = harness.write_result(root / "test_harness" / "results", record)

                passed = record["passed"]
                if arm == "with":
                    # Only "with" runs affect the exit code. A single failure makes it 1.
                    all_passed = all_passed and passed
                # Print one line per run, then where its result file was written.
                print(f"{'PASS' if passed else 'FAIL'} {skill} {case['id']} ({args.model}, {arm})")
                print(f"result: {path}")
    # 0 if every "with" run passed, otherwise 1.
    return 0 if all_passed else 1
