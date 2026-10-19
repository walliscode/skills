"""@file cli.py
@brief Command-line entry point: `python -m test_harness <module>/<skill> --case <id> -m <model>`.
"""

# Standard library: command-line parsing, deleting folders, printing errors and paths.
import argparse
import shutil
import sys
from pathlib import Path

from test_harness import harness

# The two arms every case runs under, in order: skill available, then skill denied.
ARMS = ("with", "without")


def main(argv=None):
    """@brief Run one eval case for one skill N times under each arm and report each result.

    N comes from the harness config `runs`. Each run uses a fresh workspace built
    from the case's fixtures. The "with" arm runs first, then the "without" arm.

    Exit codes: 0 if every "with" run passes, 1 if any "with" run fails, 2 for usage or opencode errors.
    A run that errors stops the loop, so earlier runs may already have written results.
    Results are written under `test_harness/results/` in the current directory.

    @param argv Argument list, or None to use sys.argv.
    @return The process exit code.
    """
    # Describe the command-line arguments: the skill path, the case id, and the model.
    parser = argparse.ArgumentParser(prog="test_harness")
    parser.add_argument("skill", help="<module>/<skill>, e.g. engineering/tdd")
    parser.add_argument("--case", required=True, help="case id from the skill's evals/evals.yaml")
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
    skill_dir = root / args.skill
    evals_file = harness.evals_path(skill_dir)
    # Stop early if the skill has no eval cases file.
    if not evals_file.is_file():
        print(f"error: no {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    try:
        # Find the requested case in the skill's evals file.
        case = harness.find_case(harness.load_cases(skill_dir), args.case)
    except KeyError:
        print(f"error: no case '{args.case}' in {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    # Check the requested model is allowed for this case before spending any runs.
    config = harness.load_config()
    models = harness.allowed_models(case, config["models"])
    if args.model not in models:
        print(f"error: model '{args.model}' must be one of: {', '.join(models)}", file=sys.stderr)
        return 2

    # Sent verbatim. Both arms run for every case: "with" leaves the skill
    # available, "without" denies it. Only the "with" arm decides the exit code,
    # since "without" is the baseline and is expected to fail the checks.
    # Starts as passing and is turned off by any failing "with" run.
    all_passed = True
    for arm in ARMS:
        # Repeat each arm N times, from the config's `runs` value.
        for _ in range(config["runs"]):
            # A new workspace for each run, so no run sees another's files.
            workspace = harness.make_workspace(root, args.skill, args.case, arm=arm)
            try:
                # Run the prompt in the workspace, then grade the result there.
                events = harness.run_opencode(case["prompt"], args.model, cwd=workspace)
                record = harness.build_record(
                    args.skill,
                    args.case,
                    args.model,
                    case,
                    events,
                    arm=arm,
                    workspace=workspace,
                    judge=lambda criteria, output: harness.grade_rubric(criteria, output, args.model),
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
            print(f"{'PASS' if passed else 'FAIL'} {args.skill} {args.case} ({args.model}, {arm})")
            print(f"result: {path}")
    # 0 if every "with" run passed, otherwise 1.
    return 0 if all_passed else 1
