"""@file cli.py
@brief Command-line entry point: `python -m test_harness <module>/<skill> --case <id> -m <model>`.
"""

import argparse
import sys
from pathlib import Path

from test_harness import harness


def main(argv=None):
    """@brief Run one eval case for one skill and report the result.

    Exit codes: 0 if all checks pass, 1 if any fail, 2 for usage or opencode errors.
    The result is written under `test_harness/results/` in the current directory.

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

    models = harness.allowed_models(case, harness.load_config_models())
    if args.model not in models:
        print(f"error: model '{args.model}' must be one of: {', '.join(models)}", file=sys.stderr)
        return 2

    # Sent verbatim. The "with" arm runs normally (#12), so whether the skill
    # gets loaded is up to the model and is recorded in skills_loaded.
    try:
        events = harness.run_opencode(case["prompt"], args.model)
    except harness.OpencodeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    record = harness.build_record(args.skill, args.case, args.model, case, events)
    path = harness.write_result(root / "test_harness" / "results", record)

    passed = record["passed"]
    print(f"{'PASS' if passed else 'FAIL'} {args.skill} {args.case} ({args.model})")
    print(f"result: {path}")
    return 0 if passed else 1
