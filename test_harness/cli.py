"""@file cli.py
@brief Command-line entry point: `python -m test_harness <module>/<skill> --case <id> -m <model>`.
"""

import argparse
import shutil
import sys
from pathlib import Path

from test_harness import harness


def main(argv=None):
    """@brief Run one eval case for one skill N times and report each result.

    N comes from the harness config `runs`. Each run uses a fresh workspace built
    from the case's fixtures.

    Exit codes: 0 if every run passes, 1 if any run fails, 2 for usage or opencode errors.
    A run that errors stops the loop, so earlier runs may already have written results.
    Results are written under `test_harness/results/` in the current directory.

    @param argv Argument list, or None to use sys.argv.
    @return The process exit code.
    """
    parser = argparse.ArgumentParser(prog="test_harness")
    parser.add_argument("skill", help="<module>/<skill>, e.g. engineering/tdd")
    parser.add_argument("--case", required=True, help="case id from the skill's evals/evals.yaml")
    parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="provider/model passed to opencode -m; must be in the config list or the case's models",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    skill_dir = root / args.skill
    evals_file = harness.evals_path(skill_dir)
    if not evals_file.is_file():
        print(f"error: no {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    try:
        case = harness.find_case(harness.load_cases(skill_dir), args.case)
    except KeyError:
        print(f"error: no case '{args.case}' in {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    config = harness.load_config()
    models = harness.allowed_models(case, config["models"])
    if args.model not in models:
        print(f"error: model '{args.model}' must be one of: {', '.join(models)}", file=sys.stderr)
        return 2

    # Sent verbatim. The "with" arm runs normally (#12), so whether the skill
    # gets loaded is up to the model and is recorded in skills_loaded.
    all_passed = True
    for _ in range(config["runs"]):
        workspace = harness.make_workspace(root, args.skill, args.case)
        try:
            events = harness.run_opencode(case["prompt"], args.model, cwd=workspace)
        except harness.OpencodeError as err:
            print(f"error: {err}", file=sys.stderr)
            return 2
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

        record = harness.build_record(args.skill, args.case, args.model, case, events)
        path = harness.write_result(root / "test_harness" / "results", record)

        passed = record["passed"]
        all_passed = all_passed and passed
        print(f"{'PASS' if passed else 'FAIL'} {args.skill} {args.case} ({args.model})")
        print(f"result: {path}")
    return 0 if all_passed else 1
